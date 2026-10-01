using System;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AutoCadMcp.ContextObserver;
internal static class PipeFixture
{
    [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] private static extern IntPtr CreateWindowExW(uint ex,string cls,string title,uint style,int x,int y,int w,int h,IntPtr parent,IntPtr menu,IntPtr module,IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool DestroyWindow(IntPtr hwnd);
    internal static void AssertNoAbandoned(UiWitnessQueue queue)
    {
        if(queue.Count!=0) throw new InvalidOperationException("transport retained abandoned work");
        queue.Drain(expected=>{throw new InvalidOperationException("abandoned sample executed");});
    }
    internal static void Run(bool stall)
    {
        if(Environment.OSVersion.Platform!=PlatformID.Win32NT) throw new Exception("Windows fixture requires Windows");
        var hwnd=CreateWindowExW(0,"STATIC","synthetic native observer fixture",0,0,0,1,1,IntPtr.Zero,IntPtr.Zero,IntPtr.Zero,IntPtr.Zero);
        if(hwnd==IntPtr.Zero) throw new Exception("fixture window unavailable");
        try
        {
            using(var queue=new UiWitnessQueue(()=>LocalPipeServer.Now))
            using(var server=new LocalPipeServer(queue))
            {
                using(var collisionQueue=new UiWitnessQueue(()=>LocalPipeServer.Now))
                {
                    bool rejected=false;
                    try {using(var duplicate=new LocalPipeServer(collisionQueue)) {}}
                    catch(NativeProtocolException error) {rejected=error.Code=="UNAVAILABLE";}
                    if(!rejected) throw new Exception("first-instance collision not rejected");
                }
                Console.WriteLine(JsonSerializer.Serialize(new {hwnd=unchecked((ulong)hwnd.ToInt64()),pipe=server.PipeName}));Console.Out.Flush();
                var state=new HostState();state.Created(1,2);int samples=0;
                var input=Task.Run(()=>Console.ReadLine());
                while(!input.IsCompleted)
                {
                    if(!stall) queue.Drain(expected=>{samples++;return state.Sample(new[]{new ObservedDocument(1,2,unchecked((ulong)hwnd.ToInt64()),null,true)},1,false,expected);});
                    Thread.Sleep(5);
                }
                if(stall) {Thread.Sleep(2100);AssertNoAbandoned(queue);if(samples!=0) throw new Exception("stalled request was sampled");}
                queue.Dispose();
            }
        }
        finally {DestroyWindow(hwnd);}
    }
}
