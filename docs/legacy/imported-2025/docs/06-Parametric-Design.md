# How-To: Parametric Design

## Overview

This guide explains how to use the parametric design features of the AutoCAD MCP Server. These features allow you to create dynamic and intelligent 3D models that can be easily modified.

## Prerequisites

*   AutoCAD MCP Server installed and running.
*   An MCP client connected to the server.

## Step-by-Step Instructions

### Creating a Parametric Model

To create a parametric model, you first need to define the parameters that will control the model's geometry. These parameters can be simple values, such as the length of a line or the radius of a circle, or they can be more complex expressions that are based on other parameters.

Once you have defined the parameters, you can then use them to create the model's geometry. For example, you could create a line whose length is controlled by a parameter, or you could create a circle whose radius is controlled by a parameter.

### Modifying a Parametric Model

To modify a parametric model, you simply need to change the values of the parameters that control the model's geometry. The model will then be automatically updated to reflect the new parameter values.

## Advanced Usage

For more advanced parametric design, you can use the `execute_python_in_autocad()` tool to execute Python code directly in AutoCAD. This allows you to use the full power of the AutoCAD API to create and modify parametric models.

## Troubleshooting

*   **Invalid Parameters:** If you are getting errors about invalid parameters, make sure that you are using valid values for the parameters.
*   **Model Not Updating:** If the model is not updating when you change the parameter values, make sure that the model is properly constrained to the parameters.

## Verification

To verify that the parametric design is working correctly, you can modify the parameter values and check that the model is updated as expected.
