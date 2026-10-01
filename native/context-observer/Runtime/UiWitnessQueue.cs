using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoCadMcp.ContextObserver
{
    public sealed class UiWitnessQueue : IDisposable
    {
        public sealed class Ticket : IDisposable
        {
            private readonly UiWitnessQueue owner;
            internal readonly ulong Hwnd;
            internal readonly double Deadline;
            internal readonly CancellationToken Cancelled;
            internal volatile bool Abandoned;
            internal bool Running;
            internal CancellationTokenRegistration Registration;
            internal readonly TaskCompletionSource<RevisionWitness> Completion = new TaskCompletionSource<RevisionWitness>(TaskCreationOptions.RunContinuationsAsynchronously);
            internal Ticket(UiWitnessQueue owner, ulong hwnd, double deadline, CancellationToken cancelled)
            { this.owner = owner; Hwnd = hwnd; Deadline = deadline; Cancelled = cancelled; }
            public Task<RevisionWitness> Task => Completion.Task;
            public void Dispose() { owner.Remove(this, "TIMEOUT"); Registration.Dispose(); }
        }
        private readonly object gate = new object();
        private readonly HashSet<Ticket> pending = new HashSet<Ticket>();
        private readonly Func<double> now;
        private readonly int uiThread = Thread.CurrentThread.ManagedThreadId;
        private volatile bool stopped;
        public UiWitnessQueue(Func<double> now) { this.now = now; }
        public int Count { get { lock (gate) return pending.Count; } }
        public Ticket Enqueue(ulong hwnd, double deadline, CancellationToken cancelled)
        {
            lock (gate)
            {
                if (stopped) throw new NativeProtocolException("UNAVAILABLE");
                if (cancelled.IsCancellationRequested || deadline <= now()) throw new NativeProtocolException("TIMEOUT");
                if (pending.Count == 4) throw new NativeProtocolException("BUSY");
                var ticket = new Ticket(this, hwnd, deadline, cancelled); pending.Add(ticket);
                ticket.Registration = cancelled.Register(() => Remove(ticket, "TIMEOUT"));
                return ticket;
            }
        }
        private void Remove(Ticket ticket, string code)
        {
            ticket.Abandoned = true;
            lock (gate) if (pending.Remove(ticket)) ticket.Completion.TrySetException(new NativeProtocolException(code));
        }
        public void Drain(Func<ulong, RevisionWitness> sample)
        {
            if (Thread.CurrentThread.ManagedThreadId != uiThread) { Dispose(); throw new NativeProtocolException("UNAVAILABLE"); }
            Ticket[] candidates;
            lock (gate) { if (stopped) return; candidates = pending.ToArray(); }
            foreach (var ticket in candidates)
            {
                lock (gate)
                {
                    if (stopped || !pending.Contains(ticket) || ticket.Running) continue;
                    if (ticket.Abandoned || ticket.Cancelled.IsCancellationRequested || ticket.Deadline <= now())
                    { Remove(ticket, "TIMEOUT"); continue; }
                    ticket.Running = true;
                }
                RevisionWitness? result = null; string? failure = null;
                try
                {
                    if (stopped) throw new NativeProtocolException("UNAVAILABLE");
                    if (ticket.Abandoned || ticket.Cancelled.IsCancellationRequested || ticket.Deadline <= now()) throw new NativeProtocolException("TIMEOUT");
                    // No queue metadata lock is held while UI-side SDK sampling runs.
                    result = sample(ticket.Hwnd);
                }
                catch (NativeProtocolException error) { failure = error.Code; }
                catch (Exception) { failure = "UNAVAILABLE"; }
                lock (gate)
                {
                    if (!pending.Remove(ticket)) continue;
                    if (stopped) failure = "UNAVAILABLE";
                    else if (ticket.Abandoned || ticket.Cancelled.IsCancellationRequested || ticket.Deadline <= now()) failure = "TIMEOUT";
                    if (failure != null) ticket.Completion.TrySetException(new NativeProtocolException(failure));
                    else ticket.Completion.TrySetResult(result!);
                }
            }
        }
        public void Dispose()
        {
            lock (gate)
            {
                stopped = true;
                foreach (var ticket in pending) ticket.Completion.TrySetException(new NativeProtocolException("UNAVAILABLE"));
                pending.Clear();
            }
        }
    }
}
