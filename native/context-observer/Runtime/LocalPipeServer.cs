using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;

namespace AutoCadMcp.ContextObserver
{
    public sealed class LocalPipeServer : IDisposable
    {
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr CreateNamedPipeW(string name, uint access, uint mode, uint instances, uint output, uint input, uint timeout, ref KernelPeer.SecurityAttributes security);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool ConnectNamedPipe(IntPtr pipe, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool DisconnectNamedPipe(IntPtr pipe);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool ReadFile(IntPtr pipe, byte[] buffer, uint count, out uint read, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool WriteFile(IntPtr pipe, byte[] buffer, uint count, out uint written, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool PeekNamedPipe(IntPtr pipe, IntPtr buffer, uint size, IntPtr read, out uint available, IntPtr remaining);
        private readonly UiWitnessQueue queue;
        private readonly ProcessIdentity owner;
        private readonly CancellationTokenSource stopped = new CancellationTokenSource();
        private readonly List<IntPtr> handles = new List<IntPtr>();
        private readonly List<Task> workers = new List<Task>();
        public static double Now => Stopwatch.GetTimestamp() / (double)Stopwatch.Frequency;
        public string PipeName { get; }
        public LocalPipeServer(UiWitnessQueue queue)
        {
            if (Environment.OSVersion.Platform != PlatformID.Win32NT) throw new NativeProtocolException("UNAVAILABLE");
            this.queue = queue; owner = KernelPeer.Read(KernelPeer.GetCurrentProcessId());
            PipeName = "autocad-mcp-context-v1-" + owner.Pid.ToString(System.Globalization.CultureInfo.InvariantCulture) + "-" + owner.Created.ToString("x16", System.Globalization.CultureInfo.InvariantCulture);
            try
            {
                IntPtr descriptor; uint length;
                KernelPeer.Require(KernelPeer.ConvertStringSecurityDescriptorToSecurityDescriptorW("D:P(A;;GRGW;;;" + owner.Sid + ")", 1, out descriptor, out length));
                try
                {
                    var security = new KernelPeer.SecurityAttributes { Length = Marshal.SizeOf(typeof(KernelPeer.SecurityAttributes)), Descriptor = descriptor, Inherit = 0 };
                    for (int index = 0; index < 4; index++)
                    {
                        // Four bounded nonblocking workers; no outstanding OVERLAPPED buffers.
                        var handle = CreateNamedPipeW("\\\\.\\pipe\\" + PipeName, 3u | (index == 0 ? 0x80000u : 0u), 1u | 8u, 4, 8196, 4100, 0, ref security);
                        KernelPeer.Require(handle != new IntPtr(-1)); handles.Add(handle);
                    }
                }
                finally { KernelPeer.LocalFree(descriptor); }
                foreach (var handle in handles) workers.Add(Task.Factory.StartNew(() => Serve(handle), CancellationToken.None, TaskCreationOptions.LongRunning, TaskScheduler.Default));
            }
            catch (Exception) { Dispose(); throw new NativeProtocolException("UNAVAILABLE"); }
        }
        private void Pause(double deadline)
        {
            if (stopped.IsCancellationRequested) throw new NativeProtocolException("UNAVAILABLE");
            if (Now >= deadline) throw new NativeProtocolException("TIMEOUT");
            stopped.Token.WaitHandle.WaitOne(5);
        }
        private byte[] Exact(IntPtr handle, int length, double deadline)
        {
            var result = new byte[length]; int offset = 0;
            while (offset < length)
            {
                Pause(deadline); var chunk = new byte[length - offset]; uint count;
                if (!ReadFile(handle, chunk, (uint)chunk.Length, out count, IntPtr.Zero))
                { if (Marshal.GetLastWin32Error() == 232) continue; throw new NativeProtocolException("UNAVAILABLE"); }
                if (count == 0) continue; Buffer.BlockCopy(chunk, 0, result, offset, (int)count); offset += (int)count;
            }
            return result;
        }
        private byte[] Request(IntPtr handle, double deadline)
        {
            var header = Exact(handle, 4, deadline); uint length = (uint)header[0] | ((uint)header[1] << 8) | ((uint)header[2] << 16) | ((uint)header[3] << 24);
            if (length == 0 || length > WireCodec.MaxRequestBytes) throw new NativeProtocolException();
            var body = Exact(handle, (int)length, deadline); var frame = new byte[body.Length + 4]; Buffer.BlockCopy(header, 0, frame, 0, 4); Buffer.BlockCopy(body, 0, frame, 4, body.Length); return frame;
        }
        private void Write(IntPtr handle, byte[] frame, double deadline)
        {
            int offset = 0;
            while (offset < frame.Length)
            {
                Pause(deadline); var chunk = new byte[frame.Length - offset]; Buffer.BlockCopy(frame, offset, chunk, 0, chunk.Length); uint count;
                KernelPeer.Require(WriteFile(handle, chunk, (uint)chunk.Length, out count, IntPtr.Zero)); offset += (int)count;
            }
        }
        private void Reply(IntPtr handle, byte[] frame, double deadline)
        {
            Write(handle, frame, deadline); uint available;
            // Wait for the client's close; DisconnectNamedPipe discards unread data.
            while (Now < deadline && !stopped.IsCancellationRequested && PeekNamedPipe(handle, IntPtr.Zero, 0, IntPtr.Zero, out available, IntPtr.Zero))
            { if (available != 0) break; stopped.Token.WaitHandle.WaitOne(5); }
        }
        private void Serve(IntPtr handle)
        {
            while (!stopped.IsCancellationRequested)
            {
                bool connected = ConnectNamedPipe(handle, IntPtr.Zero); int error = Marshal.GetLastWin32Error();
                if (connected || error != 535) { if (!connected && error != 536 && error != 232) { stopped.Cancel(); queue.Dispose(); return; } stopped.Token.WaitHandle.WaitOne(5); continue; }
                double deadline = Now + 2; string? nonce = null;
                using (var cancelled = CancellationTokenSource.CreateLinkedTokenSource(stopped.Token))
                {
                    cancelled.CancelAfter(2000);
                    try
                    {
                        uint pid; KernelPeer.Require(KernelPeer.GetNamedPipeClientProcessId(handle, out pid));
                        var peer = KernelPeer.Read(pid); KernelPeer.Authenticate(owner, peer, pid);
                        var request = WireCodec.DecodeRequest(Request(handle, deadline)); nonce = request.Nonce;
                        KernelPeer.AuthenticateConnection(owner, peer, KernelPeer.Read(pid), request.ClientPid);
                        uint available; KernelPeer.Require(PeekNamedPipe(handle, IntPtr.Zero, 0, IntPtr.Zero, out available, IntPtr.Zero));
                        if (available != 0) throw new NativeProtocolException();
                        using (var ticket = queue.Enqueue(request.DocumentHwnd, deadline, cancelled.Token))
                        {
                            while (!ticket.Task.IsCompleted)
                            {
                                Pause(deadline);
                                if (!PeekNamedPipe(handle, IntPtr.Zero, 0, IntPtr.Zero, out available, IntPtr.Zero)) throw new NativeProtocolException("UNAVAILABLE");
                                if (available != 0) throw new NativeProtocolException();
                            }
                            var witness = ticket.Task.GetAwaiter().GetResult();
                            Reply(handle, WireCodec.EncodeResponse(nonce, witness), deadline);
                        }
                    }
                    catch (NativeProtocolException failure)
                    { if (nonce != null && Now < deadline && !stopped.IsCancellationRequested) { try { Reply(handle, WireCodec.EncodeError(nonce, failure.Code), deadline); } catch (Exception) { } } }
                    catch (Exception) { }
                    finally { cancelled.Cancel(); DisconnectNamedPipe(handle); }
                }
            }
        }
        public void Dispose()
        {
            stopped.Cancel(); queue.Dispose();
            if (workers.Count > 0) Task.WaitAll(workers.ToArray(), 2100);
            foreach (var handle in handles) KernelPeer.CloseHandle(handle);
            handles.Clear();
        }
    }
}
