# How-To: Mock AutoCAD System

## Overview

This guide explains how to use the mock AutoCAD system features of the AutoCAD MCP Server. These features allow you to test your automation scripts without needing a full AutoCAD installation.

## Prerequisites

*   AutoCAD MCP Server installed and running.
*   An MCP client connected to the server.

## Step-by-Step Instructions

### Using the Mock AutoCAD System

To use the mock AutoCAD system, you first need to enable it in the server configuration. Once the mock system is enabled, all calls to the AutoCAD API will be intercepted and handled by the mock system.

The mock system provides a number of tools for testing your automation scripts. These tools allow you to simulate the behavior of the AutoCAD API, and to inspect the state of the mock AutoCAD environment.

## Advanced Usage

For more advanced testing, you can use the `execute_python_in_mock_autocad()` tool to execute Python code directly in the mock AutoCAD environment. This allows you to use the full power of the mock AutoCAD API to test your automation scripts.

## Troubleshooting

*   **Mock System Not Enabled:** If you are not seeing the expected behavior from the mock system, make sure that it is enabled in the server configuration.
*   **Invalid Mock API Calls:** If you are getting errors about invalid mock API calls, make sure that you are using the mock API correctly.

## Verification

To verify that the mock AutoCAD system is working correctly, you can execute your automation scripts and check that they behave as expected in the mock environment.
