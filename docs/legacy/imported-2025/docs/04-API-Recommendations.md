# How-To: API Recommendations

## Overview

This guide explains how to use the API recommendation features of the AutoCAD MCP Server. These features help you to discover the most efficient AutoCAD methods for specific tasks.

## Prerequisites

*   AutoCAD MCP Server installed and running.
*   An MCP client connected to the server.

## Step-by-Step Instructions

### Getting API Recommendations

To get API recommendations, use the `get_api_recommendations()` tool. This tool takes one argument: a description of the task you want to perform.

```python
client.get_api_recommendations("Find all the blocks in a drawing")
```

The server will then use its API recommendation engine to suggest the most efficient AutoCAD methods for the specified task. The recommendations will be returned to the client.

## Advanced Usage

For more advanced API recommendations, you can use the `inspect_autocad_object()` tool to inspect the properties and methods of AutoCAD objects. This can help you to better understand the AutoCAD API and discover new ways to automate your tasks.

## Troubleshooting

*   **Invalid Description:** If you are getting errors about an invalid description, make sure that you are providing a clear and concise description of the task you want to perform.
*   **No Recommendations Found:** If no recommendations are found, you can try to rephrase your description or provide more detail.

## Verification

To verify that the API recommendations are working correctly, you can try to use the recommended methods in your own scripts and check that they perform the specified task as expected.
