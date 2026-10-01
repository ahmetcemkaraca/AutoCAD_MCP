using System;
using System.Collections.Generic;
using System.Threading;

namespace AutoCadMcp.ContextObserver
{
    public sealed class SubscriptionHooks : IDisposable
    {
        private readonly int uiThread = Thread.CurrentThread.ManagedThreadId;
        private readonly List<Action> cleanup = new List<Action>();
        private bool disposed;
        private void Ui() { if (Thread.CurrentThread.ManagedThreadId != uiThread) throw new NativeProtocolException("UNAVAILABLE"); }
        public void Add(Action subscribe, Action unsubscribe)
        {
            Ui(); if (disposed) throw new NativeProtocolException("UNAVAILABLE");
            cleanup.Add(unsubscribe); // Own rollback before an SDK add can partially succeed.
            try { subscribe(); }
            catch (Exception) { try { Dispose(); } catch (NativeProtocolException) { } throw new NativeProtocolException("UNAVAILABLE"); }
        }
        public void Dispose()
        {
            Ui(); if (disposed) return; disposed = true; bool failed = false;
            for (int index = cleanup.Count - 1; index >= 0; index--) { try { cleanup[index](); } catch (Exception) { failed = true; } }
            cleanup.Clear(); if (failed) throw new NativeProtocolException("UNAVAILABLE");
        }
    }
}
