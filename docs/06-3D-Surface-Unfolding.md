# How-To: 3D Surface Unfolding (For AutoCAD Drafters)

## What This Actually Does (In AutoCAD Terms)

**The Problem You Face:**
You have a 3D solid or surface in AutoCAD (maybe a bent sheet metal part, ductwork, or curved roof panel) and you need to create a flat pattern for manufacturing, cutting, or fabrication.

**Current Manual Process:**
1.  Use AutoCAD's `FLATSHOT` command (limited results)
2.  Manually project views and trace
3.  Calculate bend allowances by hand
4.  Create multiple views to capture all surfaces
5.  **Time:** 30 minutes to 2+ hours depending on complexity

**With MCP 3D Surface Unfolding:**
1.  Select your 3D object
2.  Tell the AI what type of material/thickness
3.  Get an accurate flat pattern in under 60 seconds
4.  **Bonus:** Automatic bend line annotations and cut dimensions

## Real-World Example Walkthrough

**Scenario:** You have a rectangular duct transition (big end 24"x12", small end 12"x6") that needs to be fabricated from sheet metal.

#### Traditional Method (What You Do Now):
1.  Create auxiliary views manually
2.  Project the true shape of each face
3.  Calculate the transition curves
4.  Add bend allowances
5.  Create cutting templates
**Total time:** 45-60 minutes

#### MCP Method (New Way):
1.  **Select your 3D transition object in AutoCAD**
2.  **Open Claude Desktop and type:**

```
Please unfold this duct transition for 16-gauge galvanized steel. Show bend lines and add 1/4" flange allowances.
```

3.  **Wait 30-45 seconds**
4.  **Review the flat pattern that appears**
**Total time:** Under 2 minutes

## Step-by-Step: Your First 3D Unfolding

**What You'll Need Ready:**
*   AutoCAD open with a 3D solid or surface selected
*   The 3D object should be a simple bent shape (like an L-bracket or simple duct)

**Step 1: Prepare Your 3D Object**
1.  In AutoCAD, create or open a drawing with a 3D solid
2.  **For your first try, create something simple:**
    *   Type: `BOX` [Enter]
    *   Create a box: 10 units long, 6 units wide, 2 units high
    *   Type: `3DROTATE` [Enter]
    *   Rotate it 45 degrees to make it more interesting
3.  **Select the 3D object** (click on it so it highlights)

**Step 2: Request the Unfolding**
1.  **Open Claude Desktop**
2.  **Type this exact message:**

```
I have a 3D box selected in AutoCAD. Please unfold it into a flat pattern showing all faces with fold lines. Assume 18-gauge steel with standard bend radius.
```

3.  **Press Enter**

**Step 3: Watch the Magic**
*   The AI will analyze your 3D object
*   It will calculate the flat pattern
*   New geometry will appear in your AutoCAD drawing
*   You'll see fold lines, dimensions, and cut boundaries

**Step 4: Understand Your Results**
**What you should see:**
*   A flat pattern layout showing all faces of your box
*   Dashed lines indicating fold/bend locations
*   Dimensions for cutting
*   Potentially bend allowance calculations

**If something seems wrong:**
*   Check that your original 3D object was selected
*   Try with a simpler shape first
*   Ask the AI to explain what it did: "Can you explain how you unfolded this shape?"

## Advanced Usage (Once You're Comfortable)

**Material-Specific Unfolding:**

```
Please unfold this part for 14-gauge aluminum with a 0.125" bend radius. Include bend allowances and mark grain direction.
```

**Complex Shapes:**

```
This is a HVAC transition piece. Unfold it showing seam locations and add 1" connection flanges on both ends.
```

**Quality Control:**

```
After unfolding, please calculate the total material usage and compare it to the original 3D volume to verify accuracy.
```

## Troubleshooting Common Issues

**"The AI says it can't see my 3D object"**
*   Make sure the object is selected (highlighted) in AutoCAD
*   Try typing: "I have selected a 3D solid in AutoCAD" first

**"The flat pattern looks wrong"**
*   Ask: "Can you show me how you calculated this unfolding?"
*   Try: "Please unfold this more conservatively with larger bend radii"

**"I don't understand the result"**
*   Ask: "Can you add labels to explain each part of this flat pattern?"
*   Try: "Please add dimensions and notes to make this clear for manufacturing"

## What Makes This Different from AutoCAD's Built-in Tools

**AutoCAD's `FLATSHOT`:**
*   Only works with certain object types
*   Limited to orthographic projections
*   No bend allowance calculations
*   Manual dimension placement

**MCP 3D Surface Unfolding:**
*   Works with complex curved surfaces
*   Understands material properties
*   Automatic bend allowance calculations
*   Intelligent dimension placement
*   Can handle manufacturing constraints

## When to Use This Feature

**Perfect For:**
*   Sheet metal fabrication patterns
*   HVAC ductwork transitions
*   Architectural panel layouts
*   Custom bracket manufacturing
*   Any time you need to cut 3D shapes from flat material

**Not Ideal For:**
*   Simple rectangular cuts (overkill)
*   Objects that can't physically be unfolded
*   When you need to follow specific company standards (without training the AI first)
