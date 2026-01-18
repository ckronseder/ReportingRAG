import plotly.graph_objects as go

def create_waterfall_chart(x_labels, y_values, measures, colors=None):
    """
    Creates and returns a Plotly Figure object for a waterfall chart using dynamic data.
    """
    if not x_labels or not y_values or not measures:
        # Return an empty figure or a placeholder if no data is provided
        fig = go.Figure()
        fig.update_layout(title="Waterfall Chart (No Data Available)")
        return fig

    # Format text labels for the bars
    text_labels = [f"{val/1000:,.1f}k" for val in y_values]

    fig = go.Figure(go.Waterfall(
        name = "Breakdown", 
        orientation = "v",
        measure = measures,
        x = x_labels,
        y = y_values,
        text = text_labels,
        textposition = "outside",
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
        increasing = {"marker":{"color":"#3CB371"}}, # MediumSeaGreen for positive changes
        decreasing = {"marker":{"color":"#DC143C"}}, # Crimson for negative changes
        totals = {"marker":{"color":"#4682B4"}},     # SteelBlue for total bars
    ))

    fig.update_layout(
        title = "Erfolgsrechnung",
        showlegend = False # Typically no legend needed for simple waterfall
    )

    return fig
