# How-To: Installation & Setup (For AutoCAD Drafters)

## What This Means for You (The AutoCAD User)

**In Plain English:** This guide will walk you through the process of installing the AutoCAD MCP Server. Think of it like installing any other AutoCAD add-on or plugin. It's a one-time setup that will enable you to use AI to automate your work in AutoCAD.

**Real-World Example:**
Imagine you're installing a new plotter. You have to connect it to your computer, install the driver, and then configure it in AutoCAD. This process is very similar. You'll be installing a few programs and then telling them how to talk to each other.

**Who Should Use This:**
*   Anyone who wants to use the AutoCAD MCP Server.

**Who Should Skip This:**
*   If you have already installed the AutoCAD MCP Server, you can skip this guide.

## Before You Start - What You Need

### Physical Requirements:
*   A Windows computer (Windows 10 or newer)
*   AutoCAD 2021 or newer installed and working
*   At least 1 GB of free hard drive space
*   An internet connection

### Knowledge Check:
✅ You should be comfortable with:
*   Opening and saving AutoCAD files
*   Using AutoCAD commands from the command line
*   Installing software on Windows (like you would install AutoCAD)

❌ You do NOT need to know:
*   Programming or coding
*   Command prompt/terminal usage
*   What MCP stands for
*   How AI works

### Time Investment:
*   Initial setup: 15-20 minutes (one-time only)

## Installation (Just Like Installing AutoCAD)

**Think of this like installing any other AutoCAD add-on or plugin.**

### Step 1: Download the Required Programs

**Download #1: The Main Program (The Server)**
1.  Go to this website: [https://github.com/BarryMcAdams/AutoCAD_MCP](https://github.com/BarryMcAdams/AutoCAD_MCP)
2.  Look for the green "Code" button and click on it.
3.  In the dropdown menu, click on "Download ZIP".
4.  Save the file to your Desktop (so you can find it easily).

[SCREENSHOT: GitHub page with the "Code" button and "Download ZIP" option highlighted]

**Download #2: The Helper Program (The Client)**
1.  This is the chat window you'll use to talk to the AI. It's like a specialized AutoCAD toolbar.
2.  Go to the Claude Desktop website: [https://www.anthropic.com/claude](https://www.anthropic.com/claude)
3.  Click "Download for Windows".
4.  Save the file to your Desktop.

[SCREENSHOT: Claude Desktop website with the "Download for Windows" button highlighted]

### Step 2: Install Everything (Double-Click to Install)

**Install the Main Program:**
1.  Find the ZIP file you downloaded on your Desktop. It will be named `AutoCAD_MCP-main.zip`.
2.  Right-click on the file and select "Extract All...".
3.  In the window that appears, click "Extract". This will create a new folder on your Desktop named `AutoCAD_MCP-main`.
4.  Open the `AutoCAD_MCP-main` folder.
5.  Find the file named `install.bat` and double-click on it.
6.  A black window will appear and some text will scroll by. This is normal. It's the installer doing its work. Wait for it to finish. It will say "Installation complete" when it's done.

[SCREENSHOT: The `AutoCAD_MCP-main` folder with the `install.bat` file highlighted]

**Install the Helper Program:**
1.  Find the Claude Desktop installer you downloaded on your Desktop.
2.  Double-click on it.
3.  Follow the installation wizard (click "Next" -> "Next" -> "Install").

[SCREENSHOT: The Claude Desktop installation wizard]

### Step 3: Connect Them Together (Like Setting Up a Plotter)

**Think of this like setting up a new plotter in AutoCAD - you need to tell AutoCAD where to find it.**

1.  Open the Claude Desktop application.
2.  Look for the "Settings" menu (it might be a gear icon).
3.  In the settings, you'll see a section for "Custom Tools" or "Integrations".
4.  You'll need to add some text to tell it where to find the AutoCAD connection.
5.  Copy and paste the following text into the appropriate field:

```json
{
  "name": "AutoCAD MCP Server",
  "url": "http://localhost:8000"
}
```

[SCREENSHOT: The Claude Desktop settings window with the custom tools section highlighted and the JSON text pasted in]

## Your First Success - Prove It Works

Now that you've installed everything, let's do a simple test to make sure it's all working correctly. This will be covered in the next guide: `02-Your-First-Success.md`.
