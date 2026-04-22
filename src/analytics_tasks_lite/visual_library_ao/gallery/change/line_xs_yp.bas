Sub line_xs_yp()
    Dim ws As Worksheet
    Dim chartObj As ChartObject
    Dim chart As chart
    Dim dataRange As Range
    Dim xRange As Range
    Dim yRange As Range
    Dim series As series
    Dim lastRow As Long
    Dim dict As Object
    Dim i As Long
    Dim j As Long
    Dim key As String

    '#--------------------------------------------------------------------------
    '# Calibration start
    '#--------------------------------------------------------------------------

    ' Chart styling variables
    Dim chartFontFamily As String
    Dim chartElementsColor As Long
    Dim gridlineColor As Long

    Dim chartTitle As String
    Dim chart_title_font_size As String
    Dim xAxisTitle As String
    Dim yAxisTitle As String

    Dim xtitle_font_size As Integer
    Dim xtick_label_font_size As Integer
    Dim ytitle_font_size As Integer
    Dim ytick_label_font_size As Integer
    Dim series_label_font_size As Integer
    Dim legend_font_size As Integer
    Dim averageEntryWidth As Integer
    Dim series_weight As Double
    Dim special_series_weight As Double
    Dim special_series_name As String
    Dim marker_side As Integer
    Dim chart_width As Integer
    Dim chart_height As Integer
    Dim axis_line_weight As Double

    chartFontFamily = "Arial"
    chartElementsColor = RGB(0, 22, 94)
    gridlineColor = RGB(192, 192, 192)

    chartTitle = ""
    chart_title_font_size = 14
    xAxisTitle = "Days"
    yAxisTitle = "% of patients"

    xtitle_font_size = 10
    xtick_label_font_size = 9
    ytitle_font_size = 10
    ytick_label_font_size = 9
    series_label_font_size = 11
    legend_font_size = 9
    averageEntryWidth = 65 ' Adjusted legend width scaling
    series_weight = 1.2
    special_series_weight = 1.9     ' Thicker line weight for the special series
    special_series_name = " "  ' Name of the series to highlight
    marker_size = 6
    chart_width = 560
    chart_height = 280
    axis_line_weight = 0.75         ' Thickness of axis lines (default is 0.75)

    '#--------------------------------------------------------------------------
    '# Calibration end
    '#--------------------------------------------------------------------------

    ' Create color mapping dictionary
    Dim colorMap As Object
    Set colorMap = CreateObject("Scripting.Dictionary")

    ' Set the worksheet containing data
    Set ws = ActiveSheet

    ' Delete existing chart objects before creating new ones
    Dim existingChart As ChartObject
    For Each existingChart In ws.ChartObjects
        existingChart.Delete
    Next existingChart

    ' Find the last row of data
    lastRow = ws.Cells(Rows.count, 1).End(xlUp).Row

    ' Define X-axis range (Dates in Column A)
    Set xRange = ws.Range("A2:A" & lastRow)

    ' Generate color mapping from data
    For i = 2 To lastRow
        key = ws.Cells(i, 2).value ' Category in Column B (y)

        If Not colorMap.Exists(key) Then
            ' Parse RGB value from column E (color_rgb)
            Dim rgbText As String
            Dim rgbValues As Variant
            Dim rgbColor As Long

            rgbText = ws.Cells(i, 5).value ' Column E contains color_rgb
            rgbText = Replace(rgbText, "(", "")
            rgbText = Replace(rgbText, ")", "")
            rgbValues = Split(rgbText, ", ")

            If UBound(rgbValues) >= 2 Then
                rgbColor = RGB(CInt(rgbValues(0)), CInt(rgbValues(1)), CInt(rgbValues(2)))
                colorMap.Add key, rgbColor
            Else
                colorMap.Add key, RGB(0, 0, 0)
            End If
        End If
    Next i

    ' Initialize dictionary to store unique categories
    Set dict = CreateObject("Scripting.Dictionary")

    ' Add a chart object
    Set chartObj = ws.ChartObjects.Add(Left:=200, Width:=chart_width, Top:=50, Height:=chart_height)
    Set chart = chartObj.chart

    ' Set chart type
    chart.ChartType = xlLine
    chart.ChartArea.Font.Name = chartFontFamily
    chart.ChartArea.Font.color = chartElementsColor
    chart.ChartArea.Border.LineStyle = msoLineNone

    ' Set chart title (conditionally)
    If chartTitle <> "" Then
        chart.HasTitle = True
        chart.chartTitle.Text = chartTitle
        chart.chartTitle.Font.Size = chart_title_font_size
        chart.chartTitle.Font.Name = chartFontFamily
        chart.chartTitle.Font.color = chartElementsColor
    Else
        chart.HasTitle = False
    End If

    ' Loop through rows to collect unique categories
    For i = 2 To lastRow
        key = ws.Cells(i, 2).value

        If Not dict.Exists(key) Then
            dict.Add key, True

            Set yRange = Nothing
            For j = 2 To lastRow
                If ws.Cells(j, 2).value = key Then
                    If yRange Is Nothing Then
                        Set yRange = ws.Cells(j, 3)
                    Else
                        Set yRange = Union(yRange, ws.Cells(j, 3))
                    End If
                End If
            Next j

            ' Add the series
            Set series = chart.SeriesCollection.NewSeries
            If key = special_series_name Then
                series.Format.Line.Weight = special_series_weight
            Else
                series.Format.Line.Weight = series_weight
            End If
            series.Name = key
            series.xValues = xRange
            series.Values = yRange

            If colorMap.Exists(key) Then
                series.Format.Line.ForeColor.RGB = colorMap(key)
            Else
                series.Format.Line.ForeColor.RGB = RGB(0, 0, 0)
            End If

            With series
                .MarkerStyle = xlMarkerStyleCircle
                .MarkerSize = marker_size
                .MarkerForegroundColor = .Format.Line.ForeColor.RGB
                .MarkerBackgroundColor = .Format.Line.ForeColor.RGB
            End With
        End If
    Next i

    ' Format X-axis
    With chart.Axes(xlCategory)
        If xAxisTitle <> "" Then
            .HasTitle = True
            .AxisTitle.Text = xAxisTitle
            .AxisTitle.Font.Size = xtitle_font_size
            .AxisTitle.Font.Name = chartFontFamily
            .AxisTitle.Font.color = chartElementsColor
            .AxisTitle.Font.Bold = False
        Else
            .HasTitle = False
        End If

        .TickLabels.Font.Size = xtick_label_font_size
        .TickLabels.Font.Name = chartFontFamily
        .TickLabels.Font.color = chartElementsColor
        .Border.color = chartElementsColor
        .Border.Weight = axis_line_weight  ' Add this line to control axis line thickness
        '.MajorTickMark = xlOutside
        .MajorTickMark = xlTickMarkNone
        .Crosses = xlMinimum
        .CategoryType = xlCategoryScale
        .TickLabelSpacing = 1
        .TickMarkSpacing = 1
        .TickLabelPosition = xlTickLabelPositionLow
        .AxisBetweenCategories = False
        .CrossesAt = 1

        If lastRow > 20 Then
            .TickLabels.Orientation = 0
        End If
    End With

    ' Format Y-axis
    With chart.Axes(xlValue)
        If yAxisTitle <> "" Then
            .HasTitle = True
            .AxisTitle.Text = yAxisTitle
            .AxisTitle.Font.Size = ytitle_font_size
            .AxisTitle.Font.Name = chartFontFamily
            .AxisTitle.Font.color = chartElementsColor
            .AxisTitle.Font.Bold = False
        Else
            .HasTitle = False
        End If

        .TickLabels.Font.Size = ytick_label_font_size
        .TickLabels.Font.Name = chartFontFamily
        .TickLabels.Font.color = chartElementsColor
        .TickLabels.NumberFormat = "0%"
        .Border.color = chartElementsColor
        .Border.Weight = axis_line_weight  ' Add this line to control axis line thickness
        .MajorTickMark = xlOutside
        .MinimumScale = 0
        .MaximumScale = 1
        .MajorUnit = 0.1
        .HasMajorGridlines = True
        .MajorGridlines.Format.Line.ForeColor.RGB = gridlineColor
        .MajorGridlines.Format.Line.Weight = 0.2
        .MajorGridlines.Format.Line.DashStyle = msoLineDash ' Set gridline style to '--'
    End With

    ' Add simple value labels to the last point of each series
    For Each series In chart.SeriesCollection
        Dim lastIndex As Integer
        lastIndex = series.Points.count

        If lastIndex > 0 Then
            series.Points(lastIndex).HasDataLabel = True
            series.Points(lastIndex).DataLabel.Text = Format(series.Values(lastIndex) * 100, "0") & "%"
            series.Points(lastIndex).DataLabel.Position = xlLabelPositionAbove
            series.Points(lastIndex).DataLabel.Font.Bold = True
            series.Points(lastIndex).DataLabel.Font.Name = chartFontFamily
            series.Points(lastIndex).DataLabel.Font.color = series.Format.Line.ForeColor.RGB
            series.Points(lastIndex).DataLabel.Font.Size = series_label_font_size
        End If
    Next series

    ' Format legend
    chart.HasLegend = True
    Set Legend = chart.Legend

    With Legend
        .Position = xlLegendPositionTop
        .Left = 0
        FontSize = legend_font_size ' Your font size
        .Font.Size = FontSize
        .Font.Name = chartFontFamily ' Replace chartFontFamily with your variable or font name
        .Font.color = chartElementsColor ' Replace chartElementsColor with your variable or color

        ' Get the number of series (which equals legend entries)
        seriesCount = chart.SeriesCollection.count

        ' Approximate average width of each legend entry
        ' This is where you'll need to experiment and adjust!
        ' A rough estimate: average character width * average series name length + some spacing
        'averageEntryWidth = 60 ' Start with a guess, adjust as needed.

        ' Calculate the legend width
        legendWidth = seriesCount * averageEntryWidth

        ' Set the legend width
        .Width = legendWidth

        'Optional: Adjust Chart Area Width
        Dim chartAreaWidth As Double
        chartAreaWidth = chart.ChartArea.Width
        chart.ChartArea.Width = chartAreaWidth + (legendWidth - .Width)

    End With

    ' Cleanup
    Set ws = Nothing
    Set chartObj = Nothing
    Set chart = Nothing
    Set Legend = Nothing
    Set dataRange = Nothing
    Set xRange = Nothing
    Set yRange = Nothing
    Set dict = Nothing
    Set colorMap = Nothing
End Sub
