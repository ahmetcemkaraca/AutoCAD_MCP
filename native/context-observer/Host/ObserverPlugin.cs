using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using App = Autodesk.AutoCAD.ApplicationServices.Core.Application;
using FullApp = Autodesk.AutoCAD.ApplicationServices.Application;

[assembly: ExtensionApplication(typeof(AutoCadMcp.ContextObserver.ObserverPlugin))]
namespace AutoCadMcp.ContextObserver
{
    public sealed class ObserverPlugin : IExtensionApplication
    {
        private sealed class Subscription
        {
            internal readonly Document Document;
            internal readonly Database Database;
            private readonly Editor editor;
            private readonly ObserverPlugin owner;
            private readonly long pointer;
            internal bool Attached;
            private SubscriptionHooks hooks = new SubscriptionHooks();
            internal Subscription(Document document, ObserverPlugin owner, long pointer)
            { Document = document; Database = document.Database; editor = document.Editor; this.owner = owner; this.pointer = pointer; Attach(); }
            private void Close(object? sender, DocumentBeginCloseEventArgs args) => owner.Close(pointer, false);
            private void Aborted(object? sender, EventArgs args) => owner.Close(pointer, true);
            internal void Attach()
            {
                if (Attached) return;
                hooks = new SubscriptionHooks();
                hooks.Add(() => Document.BeginDocumentClose += Close, () => Document.BeginDocumentClose -= Close);
                hooks.Add(() => Document.CloseAborted += Aborted, () => Document.CloseAborted -= Aborted);
                hooks.Add(() => Document.ViewChanged += owner.Changed, () => Document.ViewChanged -= owner.Changed);
                hooks.Add(() => Document.CommandWillStart += owner.Changed, () => Document.CommandWillStart -= owner.Changed);
                hooks.Add(() => Document.CommandEnded += owner.Changed, () => Document.CommandEnded -= owner.Changed);
                hooks.Add(() => Document.CommandCancelled += owner.Changed, () => Document.CommandCancelled -= owner.Changed);
                hooks.Add(() => Document.CommandFailed += owner.Changed, () => Document.CommandFailed -= owner.Changed);
                hooks.Add(() => editor.EnteringQuiescentState += owner.Changed, () => editor.EnteringQuiescentState -= owner.Changed);
                hooks.Add(() => editor.LeavingQuiescentState += owner.Changed, () => editor.LeavingQuiescentState -= owner.Changed);
                hooks.Add(() => Database.ObjectOpenedForModify += owner.Changed, () => Database.ObjectOpenedForModify -= owner.Changed);
                hooks.Add(() => Database.ObjectModified += owner.Changed, () => Database.ObjectModified -= owner.Changed);
                hooks.Add(() => Database.ObjectAppended += owner.Changed, () => Database.ObjectAppended -= owner.Changed);
                hooks.Add(() => Database.ObjectErased += owner.Changed, () => Database.ObjectErased -= owner.Changed);
                hooks.Add(() => Database.ObjectUnappended += owner.Changed, () => Database.ObjectUnappended -= owner.Changed);
                hooks.Add(() => Database.ObjectReappended += owner.Changed, () => Database.ObjectReappended -= owner.Changed);
                hooks.Add(() => Database.SystemVariableWillChange += owner.Changed, () => Database.SystemVariableWillChange -= owner.Changed);
                hooks.Add(() => Database.SystemVariableChanged += owner.Changed, () => Database.SystemVariableChanged -= owner.Changed);
                hooks.Add(() => Database.BeginSave += owner.Changed, () => Database.BeginSave -= owner.Changed);
                hooks.Add(() => Database.SaveComplete += owner.Changed, () => Database.SaveComplete -= owner.Changed);
                Attached = true;
            }
            internal void Detach()
            {
                if (!Attached) return;
                hooks.Dispose(); Attached = false;
            }
        }
        private readonly HostState state = new HostState();
        private readonly Dictionary<long, Subscription> subscriptions = new Dictionary<long, Subscription>();
        private UiWitnessQueue? queue;
        private LocalPipeServer? server;
        private DocumentCollection? documents;
        private int uiThread;
        private int modal;
        private bool initialized;
        private bool Ui() => Thread.CurrentThread.ManagedThreadId == uiThread;
        private void Changed(object? sender, EventArgs args) => state.Changed();
        private void EnterModal(object? sender, EventArgs args) { Interlocked.Increment(ref modal); state.Changed(); }
        private void LeaveModal(object? sender, EventArgs args) { if (Interlocked.Decrement(ref modal) < 0) state.Lose(); state.Changed(); }
        private void Close(long pointer, bool aborted)
        { if (!Ui()) { state.Lose(); return; } if (aborted) state.CloseAborted(pointer); else state.CloseStarted(pointer); }
        private void Register(Document document, bool created)
        {
            long pointer = document.UnmanagedObject.ToInt64();
            Subscription? existing;
            if (subscriptions.TryGetValue(pointer, out existing))
            {
                if (!created) { existing.Attach(); return; }
                // Do not dereference an old SDK wrapper after native-address reuse.
                subscriptions.Remove(pointer);
            }
            if (subscriptions.Count == 128) { state.Lose(); throw new NativeProtocolException("UNAVAILABLE"); }
            state.Created(pointer, document.Database.UnmanagedObject.ToInt64());
            subscriptions.Add(pointer, new Subscription(document, this, pointer));
        }
        private void Created(object? sender, DocumentCollectionEventArgs args)
        {
            state.Changed(); if (!Ui()) { state.Lose(); return; }
            try { Register(args.Document, true); } catch (System.Exception) { state.Lose(); }
        }
        private void Destroying(object? sender, DocumentCollectionEventArgs args)
        {
            state.Changed(); if (!Ui()) { state.Lose(); return; }
            try
            {
                long pointer = args.Document.UnmanagedObject.ToInt64(); state.CloseStarted(pointer);
                Subscription? subscription; if (subscriptions.TryGetValue(pointer, out subscription)) subscription.Detach();
            }
            catch (System.Exception) { state.Lose(); }
        }
        private RevisionWitness Sample(ulong hwnd)
        {
            if (!Ui() || documents == null) { state.Lose(); throw new NativeProtocolException("UNAVAILABLE"); }
            try
            {
                long captured = state.Version;
                var active = documents.MdiActiveDocument;
                long activePointer = active == null ? 0 : active.UnmanagedObject.ToInt64();
                var live = new List<ObservedDocument>(); var pointers = new HashSet<long>(); long ownRegistrations = 0;
                foreach (Document document in documents)
                {
                    long pointer = document.UnmanagedObject.ToInt64(); pointers.Add(pointer);
                    if (!subscriptions.ContainsKey(pointer)) { Register(document, false); ownRegistrations++; }
                    var subscription = subscriptions[pointer];
                    if (!subscription.Attached) subscription.Attach();
                    long database = document.Database.UnmanagedObject.ToInt64();
                    Guid guid; Guid? fingerprint = Guid.TryParse(document.Database.FingerprintGuid, out guid) && guid != Guid.Empty ? (Guid?)guid : null;
                    bool safe = false;
                    if (pointer == activePointer)
                    {
                        var mode = document.LockMode(true);
                        safe = document.Editor.IsQuiescent && string.IsNullOrEmpty(document.CommandInProgress) &&
                            (mode == DocumentLockMode.Read || mode == DocumentLockMode.NotLocked);
                    }
                    live.Add(new ObservedDocument(pointer, database, unchecked((ulong)document.Window.Handle.ToInt64()), fingerprint, safe));
                    if (live.Count > 128) { state.Lose(); throw new NativeProtocolException("UNAVAILABLE"); }
                }
                // Removed documents were detached before destruction; never touch their SDK wrappers here.
                foreach (var pointer in subscriptions.Keys.Where(pointer => !pointers.Contains(pointer)).ToArray()) subscriptions.Remove(pointer);
                return state.Sample(live, activePointer, Volatile.Read(ref modal) != 0, hwnd, captured + ownRegistrations);
            }
            catch (NativeProtocolException) { throw; }
            catch (System.Exception) { state.Lose(); throw new NativeProtocolException("UNAVAILABLE"); }
        }
        private void Idle(object? sender, EventArgs args)
        { if (!Ui()) { state.Lose(); return; } queue?.Drain(Sample); }
        public void Initialize()
        {
            if (initialized) return; uiThread = Thread.CurrentThread.ManagedThreadId;
            try
            {
                documents = App.DocumentManager;
                documents.DocumentCreated += Created; documents.DocumentToBeDestroyed += Destroying;
                documents.DocumentDestroyed += Changed; documents.DocumentBecameCurrent += Changed; documents.DocumentActivationChanged += Changed;
                documents.DocumentLockModeWillChange += Changed; documents.DocumentLockModeChanged += Changed; documents.DocumentLockModeChangeVetoed += Changed;
                App.SystemVariableChanging += Changed; App.SystemVariableChanged += Changed;
                FullApp.EnterModal += EnterModal; FullApp.LeaveModal += LeaveModal;
                foreach (Document document in documents) Register(document, false);
                queue = new UiWitnessQueue(() => LocalPipeServer.Now); server = new LocalPipeServer(queue);
                App.Idle += Idle; initialized = true;
            }
            catch (System.Exception) { state.Lose(); Terminate(); }
        }
        public void Terminate()
        {
            state.Lose(); queue?.Dispose(); server?.Dispose();
            if (!Ui()) return;
            try
            {
                App.Idle -= Idle;
                if (documents != null)
                {
                    documents.DocumentCreated -= Created; documents.DocumentToBeDestroyed -= Destroying;
                    documents.DocumentDestroyed -= Changed; documents.DocumentBecameCurrent -= Changed; documents.DocumentActivationChanged -= Changed;
                    documents.DocumentLockModeWillChange -= Changed; documents.DocumentLockModeChanged -= Changed; documents.DocumentLockModeChangeVetoed -= Changed;
                }
                App.SystemVariableChanging -= Changed; App.SystemVariableChanged -= Changed;
                FullApp.EnterModal -= EnterModal; FullApp.LeaveModal -= LeaveModal;
                foreach (var subscription in subscriptions.Values) subscription.Detach();
                subscriptions.Clear();
            }
            catch (System.Exception) { state.Lose(); }
        }
    }
}
