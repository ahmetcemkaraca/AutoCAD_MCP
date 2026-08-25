# How-To: Basic Drawing Operations

## Overview

This guide explains how to perform basic drawing operations in AutoCAD using the MCP Server. These operations include creating simple geometric shapes, adding text and annotations, and managing layers.

## Prerequisites

*   AutoCAD MCP Server installed and running.
*   An MCP client connected to the server.

## Step-by-Step Instructions

### Creating Geometric Shapes

The MCP Server provides a number of tools for creating geometric shapes in AutoCAD. These tools can be accessed through the MCP client.

#### Creating a Line

To create a line, use the `draw_line()` tool. This tool takes four arguments: the x and y coordinates of the start point, and the x and y coordinates of the end point.

```python
client.draw_line(0, 0, 100, 100)
```

This will draw a line from (0, 0) to (100, 100) in the current AutoCAD drawing.

#### Creating a Circle

To create a circle, use the `draw_circle()` tool. This tool takes three arguments: the x and y coordinates of the center point, and the radius of the circle.

```python
client.draw_circle(50, 50, 25)
```

This will draw a circle with a center at (50, 50) and a radius of 25.

#### Creating a Rectangle

To create a rectangle, use the `draw_rectangle()` tool. This tool takes four arguments: the x and y coordinates of the lower-left corner, and the width and height of the rectangle.

```python
client.draw_rectangle(10, 10, 50, 25)
```

This will draw a rectangle with a lower-left corner at (10, 10), a width of 50, and a height of 25.

### Text and Annotation Tools

The MCP Server also provides tools for adding text and annotations to your drawings.

#### Adding Text

To add text to a drawing, use the `add_text()` tool. This tool takes three arguments: the text to add, and the x and y coordinates of the insertion point.

```python
client.add_text("Hello, world!", 20, 20)
```

This will add the text "Hello, world!" to the drawing at the point (20, 20).

### Layer Management

The MCP Server provides tools for managing layers in your drawings.

#### Creating a Layer

To create a new layer, use the `create_layer()` tool. This tool takes one argument: the name of the layer to create.

```python
client.create_layer("My Layer")
```

This will create a new layer named "My Layer" in the current drawing.

#### Setting the Current Layer

To set the current layer, use the `set_layer()` tool. This tool takes one argument: the name of the layer to set as the current layer.

```python
client.set_layer("My Layer")
```

This will set the current layer to "My Layer". All new objects will be created on this layer.

## Advanced Usage

For more advanced drawing operations, you can use the `execute_python_in_autocad()` tool to execute Python code directly in AutoCAD. This allows you to use the full power of the AutoCAD API to create and modify objects in your drawings.

## Troubleshooting

*   **Invalid Coordinates:** If you are getting errors about invalid coordinates, make sure that you are using valid numbers for the coordinates.
*   **Layer Not Found:** If you are getting errors about a layer not being found, make sure that the layer exists in the current drawing.

## Verification

To verify that the drawing operations are working correctly, you can open the drawing in AutoCAD and check that the objects have been created as expected.
