# How-To: 3D Surface Unfolding

## Overview

This guide explains how to use the 3D surface unfolding features of the AutoCAD MCP Server. These features allow you to flatten complex 3D surfaces into 2D patterns for manufacturing.

## Prerequisites

*   AutoCAD MCP Server installed and running.
*   An MCP client connected to the server.

## Step-by-Step Instructions

### Unfolding a 3D Surface

To unfold a 3D surface, use the `unfold_surface()` tool. This tool takes one argument: the 3D surface to unfold.

```python
client.unfold_surface(my_surface)
```

The server will then use its surface unfolding engine to flatten the 3D surface into a 2D pattern. The resulting pattern will be returned to the client.

## Advanced Usage

For more advanced surface unfolding, you can use the `unfold_surface_with_options()` tool. This tool allows you to specify a number of options for the unfolding process, such as the unfolding method and the desired level of accuracy.

## Troubleshooting

*   **Invalid Surface:** If you are getting errors about an invalid surface, make sure that you are providing a valid 3D surface to the `unfold_surface()` tool.
*   **Unfolding Failed:** If the unfolding process fails, you can try to use a different unfolding method or adjust the unfolding options.

## Verification

To verify that the surface unfolding is working correctly, you can open the resulting 2D pattern in AutoCAD and check that it is a valid representation of the original 3D surface.
