# How-To: AI Code Generation

## Overview

This guide explains how to use the AI-powered code generation features of the AutoCAD MCP Server. These features allow you to automatically generate AutoLISP and Python scripts to automate complex AutoCAD tasks.

## Prerequisites

*   AutoCAD MCP Server installed and running.
*   An MCP client connected to the server.

## Step-by-Step Instructions

### Generating AutoLISP Code

To generate AutoLISP code, use the `generate_autolisp_script()` tool. This tool takes one argument: a description of the task you want to perform.

```python
client.generate_autolisp_script("Draw a circle with a radius of 10 at the center of the drawing")
```

The server will then use its AI-powered code generation engine to generate an AutoLISP script that performs the specified task. The generated script will be returned to the client.

### Generating Python Code

To generate Python code, use the `generate_python_autocad_script()` tool. This tool takes one argument: a description of the functionality you want to implement.

```python
client.generate_python_autocad_script("Create a function that draws a regular polygon with a specified number of sides and radius")
```

The server will then generate a Python script that implements the specified functionality. The generated script will be returned to the client.

## Advanced Usage

For more advanced code generation, you can use the `execute_python_in_autocad()` tool to execute Python code directly in AutoCAD. This allows you to use the full power of the AutoCAD API to create and modify objects in your drawings.

## Troubleshooting

*   **Invalid Description:** If you are getting errors about an invalid description, make sure that you are providing a clear and concise description of the task you want to perform.
*   **Code Generation Failed:** If the code generation fails, you can try to rephrase your description or provide more detail.

## Verification

To verify that the code generation is working correctly, you can execute the generated script in AutoCAD and check that it performs the specified task as expected.
