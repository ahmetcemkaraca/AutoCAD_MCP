# Claude Code Monitoring Tools Guide

This guide covers two complementary monitoring tools for Claude Code usage.

## 🍋 Sniffly - Analytics Dashboard

**Purpose**: Web-based analytics dashboard for understanding Claude Code usage patterns, errors, and conversation history.

**Installation**: ✅ Installed via `pip install sniffly`

### Commands:
- `sniffly init` - Initialize and start the dashboard
- `sniffly --port 8081` - Start on specific port
- `sniffly --no-browser` - Start without auto-opening browser

### Usage:
1. Run `PYTHONIOENCODING=utf-8 sniffly init` to start the dashboard
2. Opens automatically at http://127.0.0.1:8081
3. Dashboard provides:
   - Usage pattern analysis
   - Error breakdown insights
   - Message history analysis
   - Shareable analytics

### Key Features:
- Completely local (no telemetry)
- Privacy-focused (conversations never leave computer)
- Configurable port and browser settings
- Supports remote server usage with port forwarding

---

## 📊 Claude Monitor - Token Usage Tracker

**Purpose**: Real-time terminal monitoring for token consumption and cost tracking.

**Installation**: ✅ Installed via `uv tool install claude-monitor`

### Commands:
- `claude-monitor` - Start monitoring
- `claude-code-monitor` - Alternative command
- `cmonitor` - Short alias
- `ccmonitor` - Another short alias
- `ccm` - Shortest alias

### Usage:
1. Run any of the above commands to start real-time monitoring
2. Provides live terminal display with:
   - Real-time token consumption tracking
   - Cost analysis
   - ML-based usage predictions
   - Session limit detection

### Key Features:
- Automatic plan detection (Pro/Max5/Max20)
- P90 usage analysis
- Rich, color-coded terminal UI
- Configurable refresh rates
- Timezone and theme customization
- Machine learning predictions

---

## Tool Compatibility

These tools are **completely compatible** and serve different purposes:

- **Sniffly**: Historical analysis and web-based insights
- **Claude Monitor**: Real-time monitoring and terminal-based tracking

Both tools:
- Run locally with no external dependencies
- Are privacy-focused
- Can be used simultaneously without conflicts
- Complement each other for comprehensive monitoring

## Quick Start Commands

```bash
# Start Sniffly dashboard
PYTHONIOENCODING=utf-8 sniffly init

# Start Claude Monitor in another terminal
claude-monitor
```

Both tools will run independently and provide different perspectives on your Claude Code usage.