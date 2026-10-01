# Native observer API compile preflight

Date: 2026-10-01. Evidence level: actual-reference compilation on Linux only.
No AutoCAD assembly was loaded or executed; no host compatibility gate is closed.

SDK 10.0.401 compiled an isolated IExtensionApplication probe against all three
runtime profiles. References came from the Autodesk-owned NuGet packages, with
exact versions and build-only assets. No stub SDK or runtime DLL redistribution
was used.

| Target | AutoCAD.NET | Core / Model | Fresh build |
| --- | --- | --- | --- |
| net48 | 24.0.0 | 24.0.0 / 24.0.0 | 0 warnings, 0 errors; 7.52s |
| net8.0-windows | 25.0.1 | 25.0.0 / 25.0.0 | 0 warnings, 0 errors; 7.89s |
| net10.0-windows | 25.0.2 | 25.0.2 / 25.0.2 | 0 warnings, 0 errors; 7.79s |

The project enabled Windows targeting, Windows Forms/WPF reference frameworks,
latest C# and warnings-as-errors. Framework 4.8 reference assemblies 1.0.3 were
build-only. Full AutoCAD.NET supplies the application modal events; Core alone
is insufficient for those callbacks. The full net8 package 25.0.1 is deliberate:
its declared Core 25.0.0 dependency restores cleanly, whereas full 25.0.0 requests
an unavailable 25.0.0-V058 package. No dependency-warning suppression is needed.

The compiled probe binds document create/close-start/destroy/activation events;
global lock will-change/changed/veto events and CurrentMode/MyNewMode;
Application.Idle, system-variable changes and EnterModal/LeaveModal;
Document.Window.Handle, LockMode(true), CommandInProgress and Editor.IsQuiescent;
view/command/quiescence events; Database.FingerprintGuid, open-for-modify,
modified/appended/erased/unappended/reappended, variable and save events.
The probe also references Read and NotLocked lock modes. This checks actual API
signatures; it does not prove event coverage, callback timing or idle behavior.

Commands for each isolated project:

```text
dotnet restore Probe.csproj --source https://api.nuget.org/v3/index.json --use-lock-file --verbosity quiet
dotnet build Probe.csproj --no-restore --verbosity minimal
dotnet restore Probe.csproj --locked-mode --source https://api.nuget.org/v3/index.json --verbosity quiet
```

The actual observer implementation must repeat these builds with its own source
and committed lockfiles, package only project assemblies, then run pure/Windows
pipe checks and the deferred operator AutoCAD matrix. Temporary probe source is
not a product implementation or substitute for those gates.

Primary package references: [2021](https://www.nuget.org/packages/AutoCAD.NET/24.0.0),
[2025 .NET 8](https://www.nuget.org/packages/AutoCAD.NET/25.0.1),
[updated 2025 .NET 10](https://www.nuget.org/packages/AutoCAD.NET/25.0.2).
The [Autodesk compatibility table](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Customization/files/GUID-D54B0935-1638-4F97-8B37-1EC3635A1E71.htm)
describes compatible API generations; actual release verification remains pending.
