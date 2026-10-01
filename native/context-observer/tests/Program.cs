using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using AutoCadMcp.ContextObserver;

internal static class Program
{
    private static int checks;
    private static string currentCheck = "state transitions";
    private sealed class AssertionFailure : Exception { internal AssertionFailure(string name) : base(name) { } }
    private static void Check(bool condition, string name)
    {
        checks++;
        if (!condition) throw new AssertionFailure(name);
    }
    private static void Error(string code, Action action)
    {
        try { action(); }
        catch (NativeProtocolException ex) { Check(ex.Code == code && ex.Message == code, "fixed error code"); return; }
        throw new AssertionFailure("expected " + code);
    }
    private static void StateChecks()
    {
        var state = new ObserverState();
        var first = new DocumentRegistration("lifetime-one", 0x1234, null);
        Error("UNAVAILABLE", () => state.Witness(0x1234));
        state.Reconcile(new[] { first });
        state.Activate(first.Key);
        state.ObserveReadiness(Readiness.Ready);
        var a = state.Witness(first.Hwnd);
        state.Reconcile(new[] { first }); state.ObserveReadiness(Readiness.Ready);
        Check(state.Witness(first.Hwnd).Epoch == a.Epoch, "unchanged read remains stable");
        Error("BUSY", () => state.Witness(first.Hwnd + 1));
        state.Changed(); state.ObserveReadiness(Readiness.Ready);
        var changed = state.Witness(first.Hwnd);
        state.Changed(); state.ObserveReadiness(Readiness.Ready);
        var reverted = state.Witness(first.Hwnd);
        Check(a.Epoch < changed.Epoch && changed.Epoch < reverted.Epoch, "change and revert advance");
        Check(a.SessionId == reverted.SessionId, "stable lifetime");
        state.BeginClose(first.Key);
        Error("BUSY", () => state.Witness(first.Hwnd));
        state.Reconcile(new[] { first }); state.ObserveReadiness(Readiness.Ready);
        Check(state.Witness(first.Hwnd).SessionId == a.SessionId, "cancelled close preserves");
        state.Reconcile(Array.Empty<DocumentRegistration>());
        Error("UNAVAILABLE", () => state.Witness(first.Hwnd));
        state.Reconcile(new[] { new DocumentRegistration("lifetime-two", first.Hwnd, null) });
        state.Activate("lifetime-two"); state.ObserveReadiness(Readiness.Ready);
        Check(state.Witness(first.Hwnd).SessionId != a.SessionId, "HWND reuse gets new UUID");
        Check(new ObserverState().BridgeId != state.BridgeId, "bridge restart differs");
        state.ObserveReadiness(Readiness.Busy); Error("BUSY", () => state.Witness(first.Hwnd));
        state.LoseObservation(); state.ObserveReadiness(Readiness.Ready);
        Error("UNAVAILABLE", () => state.Witness(first.Hwnd));

        var retained = new ObserverState();
        retained.Reconcile(new[] { first }); retained.Activate(first.Key); retained.ObserveReadiness(Readiness.Ready);
        var before = retained.Witness(first.Hwnd);
        retained.Reconcile(new[] { new DocumentRegistration(first.Key, first.Hwnd, Guid.NewGuid()) });
        retained.ObserveReadiness(Readiness.Ready);
        var after = retained.Witness(first.Hwnd);
        Check(after.SessionId == before.SessionId && after.Epoch > before.Epoch && after.DatabaseGuid != null, "metadata change preserves lifetime");
        retained.Reconcile(ThrowingRegistrations(first)); retained.ObserveReadiness(Readiness.Ready);
        Error("UNAVAILABLE", () => retained.Witness(first.Hwnd));

        var capped = new ObserverState();
        capped.Reconcile(Enumerable.Range(1, 128).Select(i => new DocumentRegistration("key-" + i, (ulong)i, null)).ToArray());
        capped.Activate("key-1"); capped.ObserveReadiness(Readiness.Ready);
        Check(capped.Witness(1).Epoch > 0, "128 accepted");
        capped.Reconcile(Enumerable.Range(1, 129).Select(i => new DocumentRegistration("key-" + i, (ulong)i, null)).ToArray());
        capped.Reconcile(new[] { first }); capped.Activate(first.Key); capped.ObserveReadiness(Readiness.Ready);
        Error("UNAVAILABLE", () => capped.Witness(first.Hwnd));
        var overflow = new ObserverState(Guid.NewGuid(), ulong.MaxValue, Guid.NewGuid);
        overflow.Changed(); overflow.Reconcile(new[] { first }); overflow.Activate(first.Key);
        overflow.ObserveReadiness(Readiness.Ready); Error("UNAVAILABLE", () => overflow.Witness(first.Hwnd));
        var concurrent = new ObserverState();
        concurrent.Reconcile(new[] { first }); concurrent.Activate(first.Key); concurrent.ObserveReadiness(Readiness.Ready);
        var baseEpoch = concurrent.Witness(first.Hwnd).Epoch;
        System.Threading.Tasks.Parallel.For(0, 1000, _ => concurrent.Changed());
        concurrent.ObserveReadiness(Readiness.Ready);
        Check(concurrent.Witness(first.Hwnd).Epoch == baseEpoch + 1001, "locked epoch loses no events");
        var reused = new ObserverState();
        reused.Reconcile(new[] { first }); reused.Activate(first.Key); reused.ObserveReadiness(Readiness.Ready);
        var oldSession = reused.Witness(first.Hwnd).SessionId;
        reused.Reconcile(Array.Empty<DocumentRegistration>()); reused.Reconcile(new[] { first });
        reused.Activate(first.Key); reused.ObserveReadiness(Readiness.Ready);
        Check(reused.Witness(first.Hwnd).SessionId != oldSession, "removed same key is a new lifetime");

        var invalid = new ObserverState();
        invalid.Reconcile(new[] { first, first }); invalid.Reconcile(new[] { first });
        invalid.Activate(first.Key); invalid.ObserveReadiness(Readiness.Ready);
        Error("UNAVAILABLE", () => invalid.Witness(first.Hwnd));
    }
    private static IEnumerable<DocumentRegistration> ThrowingRegistrations(DocumentRegistration first)
    {
        yield return first;
        throw new InvalidOperationException("test-only observer failure");
    }
    private static void CodecChecks(string path)
    {
        using var vectors = JsonDocument.Parse(File.ReadAllBytes(path));
        foreach (var row in vectors.RootElement.EnumerateArray())
        {
            currentCheck = row.GetProperty("name").GetString()!;
            var frame = Convert.FromHexString(row.GetProperty("frame_hex").GetString()!);
            var request = row.GetProperty("kind").GetString() == "request";
            var valid = row.GetProperty("valid").GetBoolean();
            var code = row.TryGetProperty("error", out var error) ? error.GetString() : null;
            Action action = () =>
            {
                if (request) { var value = WireCodec.DecodeRequest(frame); Check(WireCodec.DecodeRequest(WireCodec.EncodeRequest(value)).Nonce == value.Nonce, "request roundtrip"); }
                else { var value = WireCodec.DecodeResponse(frame, row.GetProperty("nonce").GetString()!); Check(WireCodec.EncodeResponse(row.GetProperty("nonce").GetString()!, value).SequenceEqual(frame), "response wire"); }
            };
            if (!valid || code != null) Error(code ?? "INVALID_REQUEST", action);
            else action();
        }
        var encoded = WireCodec.EncodeRequest(new StateRequest(new string('a', 64), 1, 1));
        Check(WireCodec.ReadFrame(new Fragmented(encoded), WireCodec.MaxRequestBytes).SequenceEqual(encoded), "fragmented frame");
        Error("INVALID_REQUEST", () => WireCodec.ReadFrame(new Fragmented(encoded.Take(encoded.Length - 1).ToArray()), WireCodec.MaxRequestBytes));
        var payload = encoded.Skip(4).Concat(Enumerable.Repeat((byte)' ', WireCodec.MaxRequestBytes - (encoded.Length - 4))).ToArray();
        Check(WireCodec.DecodeRequest(WireCodec.Frame(payload, WireCodec.MaxRequestBytes)).ClientPid == 1, "exact byte bound");
        Error("INVALID_REQUEST", () => WireCodec.Frame(payload.Concat(new byte[] { 32 }).ToArray(), WireCodec.MaxRequestBytes));
    }
    private sealed class Fragmented : MemoryStream
    {
        public Fragmented(byte[] value) : base(value) { }
        public override int Read(byte[] buffer, int offset, int count) => base.Read(buffer, offset, Math.Min(1, count));
    }
    public static int Main(string[] args)
    {
        try { StateChecks(); CodecChecks(args[0]); Console.WriteLine("Native pure checks passed: " + checks); return 0; }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Native pure check failed: " + currentCheck + " / " + ex.GetType().Name);
            if (ex is AssertionFailure) Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }
}
