using System;
using System.Collections.Generic;
using System.Globalization;

namespace AutoCadMcp.ContextObserver
{
    public sealed class NativeProtocolException : Exception
    {
        public string Code { get; }
        private static string Fixed(string code) => code == "UNAVAILABLE" || code == "BUSY" ||
            code == "INVALID_REQUEST" || code == "TIMEOUT" || code == "UNTRUSTED_PEER" ? code : "INVALID_REQUEST";
        public NativeProtocolException(string code = "INVALID_REQUEST") : base(Fixed(code)) { Code = Fixed(code); }
    }
    public sealed class RevisionWitness
    {
        public Guid BridgeId { get; }
        public Guid SessionId { get; }
        public ulong Epoch { get; }
        public Guid? DatabaseGuid { get; }
        public RevisionWitness(Guid bridgeId, Guid sessionId, ulong epoch, Guid? databaseGuid)
        {
            if (epoch == 0) throw new NativeProtocolException();
            BridgeId = bridgeId; SessionId = sessionId; Epoch = epoch; DatabaseGuid = databaseGuid;
        }
        public string OpaqueToken => "native-context-epochs-v1:" + BridgeId.ToString("D") + ":" +
            SessionId.ToString("D") + ":" + Epoch.ToString(CultureInfo.InvariantCulture);
    }
    public sealed class DocumentRegistration
    {
        public string Key { get; }
        public ulong Hwnd { get; }
        public Guid? DatabaseGuid { get; }
        public DocumentRegistration(string key, ulong hwnd, Guid? databaseGuid)
        { Key = key; Hwnd = hwnd; DatabaseGuid = databaseGuid; }
    }
    public enum Readiness { Unknown, Busy, Ready }
    public sealed class ObserverState
    {
        private sealed class DocumentState
        {
            internal readonly DocumentRegistration Registration;
            internal readonly Guid Session;
            internal bool Closing;
            internal DocumentState(DocumentRegistration registration, Guid session)
            { Registration = registration; Session = session; }
        }
        private readonly object gate = new object();
        private Dictionary<string, DocumentState> documents = new Dictionary<string, DocumentState>(StringComparer.Ordinal);
        private readonly Func<Guid> newSession;
        private ulong epoch;
        private bool lost;
        private string? active;
        private Readiness readiness = Readiness.Unknown;
        public Guid BridgeId { get; }
        public ObserverState() : this(Guid.NewGuid(), 1, Guid.NewGuid) { }
        internal ObserverState(Guid bridge, ulong initialEpoch, Func<Guid> sessionFactory)
        {
            if (initialEpoch == 0) throw new NativeProtocolException("UNAVAILABLE");
            BridgeId = bridge; epoch = initialEpoch; newSession = sessionFactory;
        }
        private void Lose() { lost = true; readiness = Readiness.Unknown; }
        private void Advance()
        {
            readiness = Readiness.Unknown;
            if (epoch == ulong.MaxValue) { Lose(); return; }
            epoch++;
        }
        public void LoseObservation() { lock (gate) { Lose(); } }
        public void Changed() { lock (gate) { if (!lost) Advance(); } }
        /// <summary>Authoritative safe UI live-set reconciliation, including terminal close cancellation.</summary>
        public void Reconcile(IEnumerable<DocumentRegistration> live)
        {
            lock (gate)
            {
                if (lost) return;
                if (live == null) { Lose(); return; }
                var replacement = new Dictionary<string, DocumentState>(StringComparer.Ordinal);
                var windows = new HashSet<ulong>();
                bool changed = false;
                try
                {
                    foreach (var registration in live)
                    {
                        if (registration == null || string.IsNullOrEmpty(registration.Key) || registration.Hwnd == 0 ||
                           replacement.Count == 128 || replacement.ContainsKey(registration.Key) || !windows.Add(registration.Hwnd))
                        { Lose(); return; }
                        DocumentState? previous;
                        if (documents.TryGetValue(registration.Key, out previous))
                        {
                            changed |= previous.Closing || previous.Registration.Hwnd != registration.Hwnd ||
                                previous.Registration.DatabaseGuid != registration.DatabaseGuid;
                            replacement.Add(registration.Key, new DocumentState(registration, previous.Session));
                        }
                        else { changed = true; replacement.Add(registration.Key, new DocumentState(registration, newSession())); }
                    }
                }
                catch (Exception) { Lose(); return; }
                changed |= documents.Count != replacement.Count;
                documents = replacement;
                if (active != null && !documents.ContainsKey(active)) active = null;
                if (changed) Advance();
            }
        }
        public void Activate(string key)
        {
            lock (gate)
            {
                if (lost) return;
                if (key == null || !documents.ContainsKey(key)) { Lose(); return; }
                active = key; Advance();
            }
        }
        public void BeginClose(string key)
        {
            lock (gate)
            {
                if (lost) return;
                DocumentState? document;
                if (key == null || !documents.TryGetValue(key, out document)) { Lose(); return; }
                document.Closing = true; Advance();
            }
        }
        /// <summary>Host-only metadata observation; no protocol endpoint accepts readiness.</summary>
        public void ObserveReadiness(Readiness value)
        {
            lock (gate)
            {
                if (lost) return;
                if (value != Readiness.Unknown && value != Readiness.Busy && value != Readiness.Ready) { Lose(); return; }
                if (readiness != value) { Advance(); if (!lost) readiness = value; }
            }
        }
        public RevisionWitness Witness(ulong hwnd)
        {
            lock (gate)
            {
                if (lost || active == null) throw new NativeProtocolException("UNAVAILABLE");
                var document = documents[active];
                if (document.Closing || readiness == Readiness.Busy || hwnd != document.Registration.Hwnd)
                    throw new NativeProtocolException("BUSY");
                if (readiness != Readiness.Ready) throw new NativeProtocolException("UNAVAILABLE");
                return new RevisionWitness(BridgeId, document.Session, epoch, document.Registration.DatabaseGuid);
            }
        }
    }
}
