# How-To: Troubleshooting Guide (For AutoCAD Drafters)

## What This Means for You (The AutoCAD User)

**In Plain English:** This guide is here to help you when things don't go as planned. It covers the most common problems you might encounter and provides simple, non-technical solutions.

**Real-World Example:**
Imagine you're trying to print a drawing, but the plotter isn't working. You'd check the cables, make sure it's turned on, and check the paper. This guide is like that, but for the AutoCAD MCP Server.

**Who Should Use This:**
*   Anyone who is having trouble with the AutoCAD MCP Server.

**Who Should Skip This:**
*   If everything is working correctly, you can skip this guide.

## Common Problems & Solutions

### The AI doesn't respond

*   **Is the server running?**
    *   Look for the black window that appeared when you started the server. If it's not open, you need to start the server again.
    *   To start the server, go to the `AutoCAD_MCP-main` folder on your Desktop and double-click on `start_server.bat`.
*   **Is AutoCAD open?**
    *   The server needs AutoCAD to be running in order to work.
*   **Is your internet connection working?**
    *   The AI needs an internet connection to work.

### The AI says it can't see your drawing

*   **Have you started a new drawing?**
    *   The AI needs an open drawing to work in.
*   **Is your drawing active?**
    *   Make sure that your drawing is the active window on your computer.

### The AI doesn't understand your command

*   **Be as clear and specific as possible.**
    *   Instead of saying "Draw a circle," say "Draw a circle with a radius of 10 at the center of the drawing."
*   **Break your command down into smaller steps.**
    *   Instead of saying "Draw a house," say "Draw a rectangle for the base. Then, draw a triangle on top for the roof."

### The AI does something unexpected

*   **Use the `undo` command.**
    *   If the AI does something you didn't expect, you can use the `undo` command in AutoCAD to undo the action.
*   **Be more specific in your command.**
    *   If the AI draws a circle that's too big, you can say "Draw a circle with a radius of 5, not 10."

### You get an error message

*   **Read the error message carefully.**
    *   The error message might give you a clue as to what went wrong.
*   **If you're still stuck, ask for help.**
    *   You can ask for help in the project's GitHub discussions.

## When to Ask for Help

If you've tried all of the solutions in this guide and you're still having trouble, don't hesitate to ask for help. The best place to get help is the project's GitHub discussions.

When you ask for help, be sure to include the following information:

*   A clear description of the problem you're having.
*   The exact command you used.
*   Any error messages you received.
*   A screenshot of your AutoCAD window.

This will help the community to understand your problem and provide you with a solution as quickly as possible.