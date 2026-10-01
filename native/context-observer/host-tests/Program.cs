using System;
using System.Linq;
using System.Threading;
using AutoCadMcp.ContextObserver;
internal static class Program {
static int checks;
static void Check(bool condition) { checks++; if(!condition) throw new Exception("assertion failed"); }
static void Error(string code, Action action) { try {action();} catch(NativeProtocolException ex) {Check(ex.Code==code && ex.Message==code); return;} throw new Exception("expected fixed failure"); }
static ObservedDocument Doc(long pointer=1, long database=2, ulong hwnd=1234, bool safe=true) => new ObservedDocument(pointer,database,hwnd,null,safe);
static System.Collections.Generic.IEnumerable<ObservedDocument> ConcurrentDiscovery(HostState state) {yield return Doc();state.Changed();yield return Doc(3,4,5678);}
static void Main(string[] args) {
if(args.Contains("--pipe-host")) {PipeFixture.Run(args.Contains("--stall"));return;}
var state=new HostState(); state.Created(1,2);
var first=state.Sample(new[]{Doc()},1,false,1234);
Check(state.Sample(new[]{Doc()},1,false,1234).OpaqueToken==first.OpaqueToken);
state.Changed(); var changed=state.Sample(new[]{Doc()},1,false,1234); Check(changed.Epoch>first.Epoch);
state.CloseStarted(1); state.CloseAborted(1);
Check(state.Sample(new[]{Doc()},1,false,1234).SessionId==first.SessionId);
Error("UNAVAILABLE",()=>state.Sample(Array.Empty<ObservedDocument>(),0,false,1234));
state.Created(1,2); var reopened=state.Sample(new[]{Doc()},1,false,1234); Check(reopened.SessionId!=first.SessionId);
state.Created(1,2); Check(state.Sample(new[]{Doc()},1,false,1234).SessionId!=reopened.SessionId);
Error("BUSY",()=>state.Sample(new[]{Doc(safe:false)},1,false,1234));
Error("BUSY",()=>state.Sample(new[]{Doc()},1,true,1234));
Error("BUSY",()=>state.Sample(new[]{Doc()},1,false,999));
var replaced=new HostState(); replaced.Created(1,2); replaced.Sample(new[]{Doc()},1,false,1234);
Error("UNAVAILABLE",()=>replaced.Sample(new[]{Doc(database:3)},1,false,1234));
Error("UNAVAILABLE",()=>replaced.Sample(new[]{Doc()},1,false,1234));
double now=0; var queue=new UiWitnessQueue(()=>now);
var one=queue.Enqueue(1234,2,CancellationToken.None);
var two=queue.Enqueue(1234,2,CancellationToken.None);
var three=queue.Enqueue(1234,2,CancellationToken.None);
var four=queue.Enqueue(1234,2,CancellationToken.None);
Error("BUSY",()=>queue.Enqueue(1234,2,CancellationToken.None));
one.Dispose(); Check(queue.Count==3); Error("TIMEOUT",()=>one.Task.GetAwaiter().GetResult());
var cancel=new CancellationTokenSource(); var five=queue.Enqueue(1234,2,cancel.Token); cancel.Cancel();
Error("TIMEOUT",()=>five.Task.GetAwaiter().GetResult()); Check(queue.Count==3);
int sampled=0; now=3; queue.Drain(hwnd=>{sampled++;return first;}); Check(sampled==0 && queue.Count==0);
Error("TIMEOUT",()=>two.Task.GetAwaiter().GetResult());
now=0; var ticket=queue.Enqueue(1234,2,CancellationToken.None); queue.Drain(hwnd=>{sampled++;Check(hwnd==1234); return first;});
Check(ticket.Task.GetAwaiter().GetResult().OpaqueToken==first.OpaqueToken); Check(sampled==1);
var abandoned=queue.Enqueue(1234,2,CancellationToken.None); queue.Dispose();
Error("UNAVAILABLE",()=>abandoned.Task.GetAwaiter().GetResult()); queue.Drain(hwnd=>{sampled++;return first;}); Check(sampled==1);
var threadBound=new UiWitnessQueue(()=>0); var pending=threadBound.Enqueue(1234,2,CancellationToken.None);
var thread=new Thread(()=>Error("UNAVAILABLE",()=>threadBound.Drain(hwnd=>first))); thread.Start();thread.Join(); Check(!pending.Task.IsCompletedSuccessfully); threadBound.Dispose();
var unknownGuid=new HostState(); var unknown=unknownGuid.Sample(new[]{new ObservedDocument(1,2,1234,Guid.Empty,true)},1,false,1234); Check(unknown.DatabaseGuid==null);
var cancelledDuringSample=new CancellationTokenSource(); var raced=new UiWitnessQueue(()=>0); var racedTicket=raced.Enqueue(1234,2,cancelledDuringSample.Token);
raced.Drain(hwnd=>{cancelledDuringSample.Cancel();return first;}); Error("TIMEOUT",()=>racedTicket.Task.GetAwaiter().GetResult()); raced.Dispose();
var owner=new ProcessIdentity(1,10,"S-1-5-21-1",2); var peer=new ProcessIdentity(2,20,owner.Sid,owner.Session);
KernelPeer.Authenticate(owner,peer,2); Error("UNTRUSTED_PEER",()=>KernelPeer.Authenticate(owner,peer,3));
Error("UNTRUSTED_PEER",()=>KernelPeer.Authenticate(owner,new ProcessIdentity(2,20,"S-1-5-21-2",2),2));
Error("UNTRUSTED_PEER",()=>KernelPeer.Authenticate(owner,new ProcessIdentity(2,20,owner.Sid,3),2));
Error("UNTRUSTED_PEER",()=>KernelPeer.AuthenticateConnection(owner,peer,new ProcessIdentity(2,21,owner.Sid,owner.Session),2));
var mixed=new HostState(); mixed.Created(1,2); mixed.Sample(new[]{Doc()},1,false,1234);
Error("BUSY",()=>mixed.Sample(ConcurrentDiscovery(mixed),1,false,1234));
int attached=0,removed=0; var hooks=new SubscriptionHooks();hooks.Add(()=>attached++,()=>{attached--;removed++;});
Error("UNAVAILABLE",()=>hooks.Add(()=>{attached++;throw new InvalidOperationException("synthetic hook failure");},()=>{attached--;removed++;}));
Check(attached==0 && removed==2);hooks.Dispose();Check(removed==2);
var entered=new ManualResetEventSlim(); var cancelledPromptly=new ManualResetEventSlim(); var slow=new UiWitnessQueue(()=>0); var slowTicket=slow.Enqueue(1234,2,CancellationToken.None);
var cancelling=new Thread(()=>{entered.Wait();slowTicket.Dispose();cancelledPromptly.Set();});cancelling.Start();
slow.Drain(hwnd=>{entered.Set();Check(cancelledPromptly.Wait(200));return first;});cancelling.Join();Error("TIMEOUT",()=>slowTicket.Task.GetAwaiter().GetResult());slow.Dispose();
Console.WriteLine("Native host/queue pure checks passed: "+checks);
}}
