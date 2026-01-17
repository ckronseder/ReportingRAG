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

    fig = go.Figure(go.Waterfall(
        name = "Breakdown",
        orientation = "v",
        measure = measures,
        x = x_labels,
        y = y_values,
        connector = {"line":{"color":"rgb(137, 148, 153)"}},
        increasing = {"marker":{"color":"rgb(63, 63, 63)"}}, # MediumSeaGreen for positive changes (dimmer green)
        decreasing = {"marker":{"color":"rgb(0, 139, 9)"}}, # Crimson for negative changes (dimmer red)
        totals = {"marker":{"color":"rgb(164, 132, 9)"}},     # SteelBlue for total bars (dimmer blue)
        # marker = {"color": colors} if colors else None # Use provided colors array if available
    ))

    fig.update_layout(
        title = "Erfolgsrechnung",
        showlegend = False # Typically no legend needed for simple waterfall
    )

    return fig
