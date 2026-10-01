using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;

namespace AutoCadMcp.ContextObserver
{
    public sealed class ObservedDocument
    {
        public long Pointer { get; }
        public long DatabasePointer { get; }
        public ulong Hwnd { get; }
        public Guid? DatabaseGuid { get; }
        public bool Safe { get; }
        public ObservedDocument(long pointer, long databasePointer, ulong hwnd, Guid? databaseGuid, bool safe)
        { Pointer = pointer; DatabasePointer = databasePointer; Hwnd = hwnd; DatabaseGuid = databaseGuid; Safe = safe; }
    }
    public sealed class HostState
    {
        private sealed class Lifetime
        {
            internal readonly string Key = Guid.NewGuid().ToString("D");
            internal readonly long Database;
            internal bool Registered;
            internal Lifetime(long database) { Database = database; }
        }
        private readonly ObserverState state = new ObserverState();
        private readonly Dictionary<long, Lifetime> lifetimes = new Dictionary<long, Lifetime>();
        private readonly int uiThread = Thread.CurrentThread.ManagedThreadId;
        private string? active;
        private long changes;
        private readonly object changeGate = new object();
        public long Version { get { lock (changeGate) return changes; } }
        public void Changed() { lock (changeGate) { state.Changed(); changes++; } }
        public void Lose() { lock (changeGate) { state.LoseObservation(); changes++; } }
        private void Ui() { if (Thread.CurrentThread.ManagedThreadId != uiThread) { Lose(); throw new NativeProtocolException("UNAVAILABLE"); } }
        public void Created(long pointer, long database)
        {
            Ui(); Changed();
            if (pointer == 0 || database == 0 || (!lifetimes.ContainsKey(pointer) && lifetimes.Count == 128)) { Lose(); return; }
            // A creation notification always denotes a new lifetime, even when native addresses repeat.
            lifetimes[pointer] = new Lifetime(database);
        }
        public void CloseStarted(long pointer)
        {
            Ui(); Changed(); Lifetime? lifetime;
            if (lifetimes.TryGetValue(pointer, out lifetime) && lifetime.Registered) state.BeginClose(lifetime.Key);
        }
        public void CloseAborted(long pointer) { Ui(); Changed(); }
        public RevisionWitness Sample(IEnumerable<ObservedDocument> observed, long activePointer, bool modal, ulong expectedHwnd, long? capturedVersion = null)
        {
            Ui(); long before = capturedVersion ?? Version; long ownDiscoveries = 0;
            try
            {
                var rows = new List<ObservedDocument>(); var pointers = new HashSet<long>();
                foreach (var row in observed)
                {
                    if (row == null || row.Pointer == 0 || row.DatabasePointer == 0 || rows.Count == 128 || !pointers.Add(row.Pointer))
                    { Lose(); throw new NativeProtocolException("UNAVAILABLE"); }
                    Lifetime? lifetime;
                    if (!lifetimes.TryGetValue(row.Pointer, out lifetime)) { Created(row.Pointer, row.DatabasePointer); lifetime = lifetimes[row.Pointer]; ownDiscoveries++; }
                    if (lifetime.Database != row.DatabasePointer) { Lose(); throw new NativeProtocolException("UNAVAILABLE"); }
                    rows.Add(row);
                }
                foreach (var key in lifetimes.Keys.Where(key => !pointers.Contains(key)).ToArray()) lifetimes.Remove(key);
                lock (changeGate)
                {
                    if (before + ownDiscoveries != changes) throw new NativeProtocolException("BUSY");
                    state.Reconcile(rows.Select(row => new DocumentRegistration(lifetimes[row.Pointer].Key, row.Hwnd, row.DatabaseGuid == Guid.Empty ? (Guid?)null : row.DatabaseGuid)));
                    foreach (var row in rows) lifetimes[row.Pointer].Registered = true;
                    var current = rows.FirstOrDefault(row => row.Pointer == activePointer);
                    if (current == null) { state.ObserveReadiness(Readiness.Unknown); active = null; throw new NativeProtocolException("UNAVAILABLE"); }
                    var activeKey = lifetimes[current.Pointer].Key;
                    if (active != activeKey) { state.Activate(activeKey); active = activeKey; }
                    state.ObserveReadiness(!modal && current.Safe ? Readiness.Ready : Readiness.Busy);
                    var witness = state.Witness(expectedHwnd);
                    return witness;
                }
            }
            catch (NativeProtocolException) { throw; }
            catch (Exception) { Lose(); throw new NativeProtocolException("UNAVAILABLE"); }
        }
    }
}
