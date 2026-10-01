# How-To: Your First Success (For AutoCAD Drafters)

## What This Means for You (The AutoCAD User)

**In Plain English:** This guide will walk you through a simple, 5-minute test to make sure that the AutoCAD MCP Server is working correctly. This is the most important step in the process, because if this works, everything else will work too.

**Real-World Example:**
Imagine you've just installed a new printer. The first thing you do is print a test page to make sure it's working. This is the same thing. We're going to ask the AI to draw a simple rectangle in AutoCAD to make sure that the connection is working.

**Who Should Use This:**
*   Anyone who has just installed the AutoCAD MCP Server.

**Who Should Skip This:**
*   If you have already completed this test and verified that the server is working, you can skip this guide.

## Before You Start - What You Need

### Physical Requirements:
*   Your computer with AutoCAD and the AutoCAD MCP Server installed.

### Knowledge Check:
✅ You should be comfortable with:
*   Opening and saving AutoCAD files.
*   Starting a new drawing in AutoCAD.

❌ You do NOT need to know:
*   Anything about coding or programming.

### Time Investment:
*   5 minutes

## Your First Success - Prove It Works

**Let's do something simple to make sure everything is connected properly.**

### The 5-Minute Test:
**What we're going to do:** Ask the AI to draw a simple rectangle in AutoCAD
**Why this matters:** If this works, everything else will work

### Step-by-Step:
1.  **Start the AutoCAD MCP Server:**
    *   Open the `AutoCAD_MCP-main` folder on your Desktop.
    *   Find the file named `start_server.bat` and double-click on it.
    *   A black window will appear and some text will scroll by. This is the server starting up. You need to leave this window open while you are using the server.

[SCREENSHOT: The `AutoCAD_MCP-main` folder with the `start_server.bat` file highlighted]

2.  **Open AutoCAD** (like you normally do)
3.  **Start a new drawing** (use your usual template)
4.  **Open Claude Desktop** (the helper program you installed)
5.  **In Claude Desktop, type exactly this:**

```
Please draw a rectangle in AutoCAD with corners at (0,0) and (10,10)
```

6.  **Press Enter and wait** (should take 2-3 seconds)
7.  **Look at your AutoCAD screen** - you should see a rectangle appear

### What Success Looks Like:
*   A rectangle appears in your AutoCAD drawing automatically.
*   You didn't have to type any AutoCAD commands.
*   The black server window shows some new text, indicating that it received and processed your request.

[SCREENSHOT: AutoCAD with the newly drawn rectangle, and the Claude Desktop window next to it with the command that was typed]

### If It Doesn't Work:
*   **The rectangle doesn't appear:**
    *   Make sure that the AutoCAD MCP Server is running (the black window is open).
    *   Make sure that you have started a new drawing in AutoCAD.
    *   Make sure that you have typed the command exactly as it appears above.
*   **You get an error message in Claude Desktop:**
    *   Read the error message carefully. It might give you a clue as to what went wrong.
    *   If you're still stuck, you can ask for help in the project's GitHub discussions.

### Celebrate! 🎉

**You just used AI to control AutoCAD!** Everything else we'll learn builds on this same principle. You are now ready to explore the other features of the AutoCAD MCP Server.
