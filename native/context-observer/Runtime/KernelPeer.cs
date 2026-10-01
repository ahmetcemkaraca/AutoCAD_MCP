using System;
using System.Runtime.InteropServices;

namespace AutoCadMcp.ContextObserver
{
    public sealed class ProcessIdentity
    {
        public uint Pid { get; }
        public ulong Created { get; }
        public string Sid { get; }
        public uint Session { get; }
        public ProcessIdentity(uint pid, ulong created, string sid, uint session) { Pid = pid; Created = created; Sid = sid; Session = session; }
        public bool SameUserSession(ProcessIdentity other) => Sid == other.Sid && Session == other.Session;
    }
    internal static class KernelPeer
    {
        [StructLayout(LayoutKind.Sequential)] internal struct FileTime { internal uint Low, High; internal ulong Value => ((ulong)High << 32) | Low; }
        [StructLayout(LayoutKind.Sequential)] internal struct SecurityAttributes { internal int Length; internal IntPtr Descriptor; internal int Inherit; }
        [DllImport("kernel32.dll")] internal static extern uint GetCurrentProcessId();
        [DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
        [DllImport("kernel32.dll", SetLastError = true)] internal static extern bool CloseHandle(IntPtr handle);
        [DllImport("kernel32.dll")] private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetProcessTimes(IntPtr handle, out FileTime created, out FileTime exit, out FileTime kernel, out FileTime user);
        [DllImport("kernel32.dll", SetLastError = true)] private static extern bool ProcessIdToSessionId(uint pid, out uint session);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] private static extern bool GetTokenInformation(IntPtr token, int type, IntPtr buffer, uint length, out uint returned);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern bool ConvertSidToStringSidW(IntPtr sid, out IntPtr text);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] internal static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string text, uint revision, out IntPtr descriptor, out uint length);
        [DllImport("kernel32.dll")] internal static extern IntPtr LocalFree(IntPtr memory);
        [DllImport("kernel32.dll", SetLastError = true)] internal static extern bool GetNamedPipeClientProcessId(IntPtr pipe, out uint pid);
        internal static void Require(bool ok) { if (!ok) throw new NativeProtocolException("UNAVAILABLE"); }
        internal static ProcessIdentity Read(uint pid)
        {
            var process = OpenProcess(0x1000 | 0x100000, false, pid); Require(process != IntPtr.Zero);
            try
            {
                Require(WaitForSingleObject(process, 0) == 258);
                FileTime created, exit, kernel, user; Require(GetProcessTimes(process, out created, out exit, out kernel, out user));
                uint session; Require(ProcessIdToSessionId(pid, out session));
                IntPtr token; Require(OpenProcessToken(process, 8, out token));
                try
                {
                    uint length; GetTokenInformation(token, 1, IntPtr.Zero, 0, out length); Require(length > 0 && length <= 4096);
                    var buffer = Marshal.AllocHGlobal((int)length);
                    try
                    {
                        Require(GetTokenInformation(token, 1, buffer, length, out length));
                        IntPtr text; Require(ConvertSidToStringSidW(Marshal.ReadIntPtr(buffer), out text));
                        try { return new ProcessIdentity(pid, created.Value, Marshal.PtrToStringUni(text)!, session); }
                        finally { LocalFree(text); }
                    }
                    finally { Marshal.FreeHGlobal(buffer); }
                }
                finally { CloseHandle(token); }
            }
            finally { CloseHandle(process); }
        }
        internal static void AuthenticateConnection(ProcessIdentity owner, ProcessIdentity original, ProcessIdentity current, uint claimed)
        { Authenticate(owner, current, claimed); if (original.Pid != current.Pid || original.Created != current.Created || original.Sid != current.Sid || original.Session != current.Session) throw new NativeProtocolException("UNTRUSTED_PEER"); }
        internal static void Authenticate(ProcessIdentity owner, ProcessIdentity client, uint claimed)
        { if (owner.Session == 0 || client.Pid != claimed || !owner.SameUserSession(client)) throw new NativeProtocolException("UNTRUSTED_PEER"); }
    }
}
