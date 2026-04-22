Sub bar_stk_xs_yp()
    Dim ws As Worksheet
    Dim chartObj As ChartObject
    Dim chart As chart
    Dim lastRow As Long
    Dim i As Long, j As Long
    Dim uniqueCategories As Object
    Dim uniqueYValues As Object
    Dim categoryYValues As Object
    Dim outputCol As Long
    Dim outputRow As Long
    Dim colorMap As Object
    Dim totalValue As Double

    Dim chartFontFamily As String
    Dim chartElementsColor As Long
    Dim gridlineColor As Long
    Dim chart_title_font_size As String
    Dim xtitle_font_size As Integer
    Dim xtick_label_font_size As Integer
    Dim ytitle_font_size As Integer
    Dim ytick_label_font_size As Integer
    Dim series_label_font_size As Integer
    Dim legend_font_size As Integer
    Dim legend_visible As Boolean
    Dim y_axis_unit As Integer
    Dim total_format As String
    Dim bar_width As Integer
    Dim label_format As String
    Dim chart_width As Integer
    Dim chart_height As Integer
    Dim hideLabel As Double

    Dim chartTitle As String
    Dim xAxisTitle As String
    Dim yAxisTitle As String
    Dim sort_array As Variant

    '#--------------------------------------------------------------------------
    '#··· Calibration start                                                  ···
    '#--------------------------------------------------------------------------

    chartFontFamily = "Arial"
    chartElementsColor = RGB(0, 22, 94)
    gridlineColor = RGB(242, 242, 242)
    chart_title_font_size = 14
    xtitle_font_size = 9
    xtick_label_font_size = 8
    ytitle_font_size = 9
    ytick_label_font_size = 10
    series_label_font_size = 9
    legend_font_size = 10
    legend_visible = True
    y_axis_unit = 20000
    total_format = "0%" ' Changed from #K format to percentage format
    bar_width = 100
    label_format = "0%" '"0.0%";
    chart_width = 400
    chart_height = 300
    hideLabel = 0.01 ' Hide labels below certain %

    chartTitle = " "
    xAxisTitle = ""
    yAxisTitle = ""

    ' Define the sorting array (can be "" for default sorting)
    sort_array = Array(" ")

    '#--------------------------------------------------------------------------
    '#··· Calibration end                                                    ···
    '#--------------------------------------------------------------------------

    ' Set active sheet
    Set ws = ActiveSheet

    ' Find last row of data
    lastRow = ws.Cells(Rows.Count, 1).End(xlUp).Row

    ' Create dictionaries for unique categories, Y values, and color mapping
    Set uniqueCategories = CreateObject("Scripting.Dictionary")
    Set uniqueYValues = CreateObject("Scripting.Dictionary")
    Set colorMap = CreateObject("Scripting.Dictionary")
    Set categoryYValues = CreateObject("Scripting.Dictionary")

    ' Collect unique categories and Y values, and store color mappings
    For i = 2 To lastRow
        Dim categoryKey As Variant
        Dim yValueKey As Variant
        categoryKey = ws.Cells(i, 1).value ' X category in Column A
        yValueKey = ws.Cells(i, 2).value   ' Y category in Column B

        If Not uniqueCategories.Exists(categoryKey) Then uniqueCategories.Add categoryKey, 0
        If Not uniqueYValues.Exists(yValueKey) Then uniqueYValues.Add yValueKey, 0

        Dim rgbText As String
        Dim rgbValues As Variant
        Dim rgbColor As Long
        rgbText = ws.Cells(i, 5).value
        rgbText = Replace(rgbText, "(", "")
        rgbText = Replace(rgbText, ")", "")
        rgbValues = Split(rgbText, ", ")

        If UBound(rgbValues) >= 2 Then
            rgbColor = RGB(CInt(rgbValues(0)), CInt(rgbValues(1)), CInt(rgbValues(2)))
            If Not colorMap.Exists(yValueKey) Then colorMap.Add yValueKey, rgbColor
        Else
            If Not colorMap.Exists(yValueKey) Then colorMap.Add yValueKey, RGB(0, 0, 0)
        End If

        Dim categoryYKey As String
        categoryYKey = categoryKey & "|" & yValueKey
        If Not categoryYValues.Exists(categoryYKey) Then
            categoryYValues.Add categoryYKey, ws.Cells(i, 3).value
        Else
            categoryYValues(categoryYKey) = categoryYValues(categoryYKey) + ws.Cells(i, 3).value
        End If
    Next i

    ' Transpose data to wide format starting from column O (15)
    outputCol = 15 ' Start at column O
    outputRow = 1  ' Header row for categories

    ' Write category headers starting from column P (outputCol + 1)
    ws.Cells(outputRow, outputCol).value = "Category"
    j = 0
    For Each categoryKey In uniqueCategories.Keys
        j = j + 1
        ws.Cells(outputRow, outputCol + j).value = categoryKey
    Next categoryKey

    ' Sort Y values based on sort_array or ascending order
    Dim sortedYValues As Variant
    If IsMissingOrEmpty(sort_array) Or (IsArray(sort_array) And ArrayLength(sort_array) = 0) Or (IsArray(sort_array) And sort_array(0) = " ") Then
        ' Default sorting: ascending order of Y value names
        sortedYValues = uniqueYValues.Keys
        Dim temp As Variant, k As Long, l As Long
        For k = LBound(sortedYValues) To UBound(sortedYValues) - 1
            For l = k + 1 To UBound(sortedYValues)
                If sortedYValues(k) > sortedYValues(l) Then
                    temp = sortedYValues(k)
                    sortedYValues(k) = sortedYValues(l)
                    sortedYValues(l) = temp
                End If
            Next l
        Next k
    Else
        ' Custom sorting based on sort_array - filter out empty entries
        Dim filteredArray() As Variant
        Dim arrayIndex As Long
        arrayIndex = 0

        For k = LBound(sort_array) To UBound(sort_array)
            If Trim(sort_array(k)) <> "" And uniqueYValues.Exists(sort_array(k)) Then
                ReDim Preserve filteredArray(arrayIndex)
                filteredArray(arrayIndex) = sort_array(k)
                arrayIndex = arrayIndex + 1
            End If
        Next k

        If arrayIndex > 0 Then
            sortedYValues = filteredArray
        Else
            ' Fallback to default sorting if no valid entries found
            sortedYValues = uniqueYValues.Keys
        End If
    End If

    ' Write Y value headers and values based on sorted order
    outputRow = 2
    For Each yValueKey In sortedYValues
        If uniqueYValues.Exists(yValueKey) Then ' Ensure Y value exists in data
            ws.Cells(outputRow, outputCol).value = yValueKey
            j = 0
            For Each categoryKey In uniqueCategories.Keys
                j = j + 1
                Dim fullKey As String
                fullKey = categoryKey & "|" & yValueKey
                If categoryYValues.Exists(fullKey) Then
                    ws.Cells(outputRow, outputCol + j).value = categoryYValues(fullKey)
                Else
                    ws.Cells(outputRow, outputCol + j).value = 0
                End If
            Next categoryKey
            outputRow = outputRow + 1
        End If
    Next yValueKey

    ' Add a row for totals below the categories (sum of percentages)
    ws.Cells(outputRow, outputCol).value = "Total"
    For j = 1 To uniqueCategories.Count
        totalValue = 0
        For i = 2 To outputRow - 1
            totalValue = totalValue + ws.Cells(i, outputCol + j).value
        Next i
        ws.Cells(outputRow, outputCol + j).value = totalValue
        ' Format the total cell as percentage
        ws.Cells(outputRow, outputCol + j).NumberFormat = "0.0%"
    Next j

    ' Store the total row number for reference
    Dim totalRow As Long
    totalRow = outputRow

    ' Remove any existing charts
    For Each chartObj In ws.ChartObjects
        chartObj.Delete
    Next chartObj

    ' Create chart object
    Set chartObj = ws.ChartObjects.Add(Left:=200, Width:=chart_width, Top:=50, Height:=chart_height)
    Set chart = chartObj.chart

    chart.ChartType = xlColumnStacked
    chart.ChartArea.Font.Name = chartFontFamily
    chart.ChartArea.Font.color = chartElementsColor
    chart.ChartArea.Border.LineStyle = msoLineNone

    ' Adjust the width of the bars
    With chart.ChartGroups(1)
        .GapWidth = bar_width ' Set the gap width to 100% (adjust this value as needed)
    End With

    If chartTitle <> "" Then
        chart.HasTitle = True
        chart.chartTitle.Text = chartTitle
        chart.chartTitle.Font.Size = chart_title_font_size
        chart.chartTitle.Font.Name = chartFontFamily
        chart.chartTitle.Font.color = chartElementsColor
    Else
        chart.HasTitle = False
    End If

    ' Increase space between the chart title and the chart
    With chart
        ' Move the plot area down by increasing its Top property
        .PlotArea.Top = .PlotArea.Top + 20 ' Adjust 20 as needed
    End With

    ' Set up the source data using the original percentage values
    Dim dataRange As Range
    Set dataRange = ws.Range(ws.Cells(2, outputCol), ws.Cells(totalRow - 1, outputCol + uniqueCategories.Count))
    chart.SetSourceData Source:=dataRange

    With chart.Axes(xlCategory)
        ' Check if X-axis title is empty before setting it
        If Trim(xAxisTitle) <> "" Then
            .HasTitle = True
            .AxisTitle.Text = xAxisTitle
            .AxisTitle.Font.Size = xtitle_font_size
            .AxisTitle.Font.Bold = False
        Else
            .HasTitle = False
        End If
        .TickLabels.Font.Size = xtick_label_font_size
        .TickLabels.Font.Name = chartFontFamily
        .TickLabelPosition = xlTickLabelPositionLow
        .MajorTickMark = xlTickMarkNone
        ' Remove date formatting for categorical data
        .TickLabels.NumberFormat = "General"
        Dim categoryLabels As Range
        Set categoryLabels = ws.Range(ws.Cells(1, outputCol + 1), ws.Cells(1, outputCol + uniqueCategories.Count))
        chart.SeriesCollection(1).XValues = categoryLabels
    End With

    With chart.Axes(xlValue)
        ' Check if Y-axis title is empty before setting it
        If Trim(yAxisTitle) <> "" Then
            .HasTitle = True
            .AxisTitle.Text = yAxisTitle
            .AxisTitle.Font.Size = ytitle_font_size
            .AxisTitle.Font.Bold = False
        Else
            .HasTitle = False
        End If
        .TickLabels.Font.Size = ytick_label_font_size
        .TickLabels.Font.Name = chartFontFamily
        .MinimumScale = 0
        .MaximumScale = 1
        .MajorUnit = 0.2 ' 20% intervals
        .HasMajorGridlines = False
        .MajorGridlines.Format.Line.ForeColor.RGB = gridlineColor
        .MajorTickMark = xlTickMarkNone
        .Border.LineStyle = xlNone
        .TickLabels.NumberFormat = "0%"
        .TickLabelPosition = xlNone ' Hides the labels
        .Border.LineStyle = xlNone ' Hides the axis line
    End With

    ' Apply colors and data labels to series
    Dim seriesIndex As Long
    For seriesIndex = 1 To chart.SeriesCollection.Count
        Dim seriesName As String
        seriesName = chart.SeriesCollection(seriesIndex).Name
        With chart.SeriesCollection(seriesIndex)
            If colorMap.Exists(seriesName) Then
                .Format.Fill.ForeColor.RGB = colorMap(seriesName)
            Else
                .Format.Fill.ForeColor.RGB = RGB(0, 0, 0)
            End If
            .HasDataLabels = True

            ' Hide data labels below the threshold for each point
            Dim pointIdx As Long
            For pointIdx = 1 To .Points.Count
                ' Get the value of this specific data point
                Dim pointValue As Double
                ' Calculate the correct row and column from the data area
                Dim dataRow As Long, dataCol As Long
                dataRow = 1 + seriesIndex
                dataCol = outputCol + pointIdx

                ' Read the value from the data table
                pointValue = ws.Cells(dataRow, dataCol).value

                ' Only show labels for points above the threshold
                If pointValue < hideLabel Then
                    .Points(pointIdx).HasDataLabel = False
                Else
                    .Points(pointIdx).HasDataLabel = True
                    With .Points(pointIdx).DataLabel
                        .ShowValue = True
                        .Position = xlLabelPositionCenter
                        .Font.Name = chartFontFamily
                        .Font.Size = series_label_font_size
                        .Font.color = RGB(255, 255, 255)
                        .NumberFormat = label_format
                    End With
                End If
            Next pointIdx
        End With
    Next seriesIndex

    On Error Resume Next
    For seriesIndex = 1 To chart.SeriesCollection.Count - 1
        Dim yValueName As String
        yValueName = ws.Cells(1 + seriesIndex, outputCol).value
        If Len(Trim(yValueName)) > 0 Then
            chart.SeriesCollection(seriesIndex).Name = yValueName
        End If
    Next seriesIndex
    On Error GoTo 0

    ' Add total values as a line series (percentage totals)
    Dim totalSeries As series
    Set totalSeries = chart.SeriesCollection.NewSeries
    With totalSeries
        .Name = "Total"
        .Values = ws.Range(ws.Cells(totalRow, outputCol + 1), ws.Cells(totalRow, outputCol + uniqueCategories.Count))
        .ChartType = xlLine
        .Format.Line.Visible = msoFalse  ' Make the line invisible
        .MarkerStyle = xlMarkerStyleNone ' Remove markers
        .HasDataLabels = True
        With .DataLabels
            .ShowValue = True
            .Position = xlLabelPositionAbove
            .Font.Name = chartFontFamily
            .Font.Size = series_label_font_size
            .Font.Bold = False
            .Font.color = chartElementsColor
            .NumberFormat = total_format ' Format as percentage
        End With
    End With

    ' Create a secondary axis for the Total line series
    totalSeries.AxisGroup = xlSecondary

    With chart.Axes(xlValue, xlSecondary)
        .Border.LineStyle = xlLineNone ' Hide the axis line
        .MajorTickMark = xlTickMarkNone ' Hide major tick marks
        .MinorTickMark = xlTickMarkNone ' Hide minor tick marks
        .TickLabels.Font.color = RGB(255, 255, 255) ' Hide tick labels by making them white
        .TickLabels.Font.Bold = False
        .TickLabelPosition = xlNone
        .Border.LineStyle = xlNone
    End With

    ' Hide "Total" from the legend by setting its name to an empty string
    For seriesIndex = 1 To chart.SeriesCollection.Count
        If chart.SeriesCollection(seriesIndex).Name = "Total" Then
            chart.SeriesCollection(seriesIndex).Name = "" ' Clear the series name
            Exit For
        End If
    Next seriesIndex

    ' Manually adjust the position of the data labels to ensure they are aligned horizontally
    Dim maxTotalValue As Double
    maxTotalValue = 0
    For j = 1 To uniqueCategories.Count
        If ws.Cells(totalRow, outputCol + j).value > maxTotalValue Then
            maxTotalValue = ws.Cells(totalRow, outputCol + j).value
        End If
    Next j

    ' Calculate a fixed vertical position for all data labels
    Dim fixedLabelTop As Double
    fixedLabelTop = chart.PlotArea.InsideTop + -13 ' Adjust 10 as needed for spacing

    ' Loop through each data point in the Total series and set the label position
    Dim pointIndex As Long
    For pointIndex = 1 To totalSeries.Points.Count
        With totalSeries.Points(pointIndex).DataLabel
            .Top = fixedLabelTop ' Set all labels to the same vertical position
        End With
    Next pointIndex

    ' Set legend visibility based on the variable
    With chart
        .HasLegend = legend_visible ' Use the variable to toggle legend
        If .HasLegend Then ' Only configure legend properties if it's visible
            With .Legend
                .Position = xlLegendPositionTop
                .Left = 0
                .Top = 0 ' Adjust this value to position the legend vertically
                .Font.Name = chartFontFamily
                .Font.Size = legend_font_size
                .Font.color = chartElementsColor
            End With

            ' Increase space between the legend and the chart dynamically
            Dim legendHeight As Double
            legendHeight = .Legend.Height ' Get the height of the legend
            .PlotArea.Top = .Legend.Top + legendHeight + 13 ' Add extra space (13 points)
        Else
            ' If legend is off, adjust PlotArea.Top to avoid unnecessary spacing
            .PlotArea.Top = 20 ' Default spacing when no legend is present
        End If
    End With

    Set ws = Nothing
    Set chartObj = Nothing
    Set chart = Nothing
    Set uniqueCategories = Nothing
    Set uniqueYValues = Nothing
    Set colorMap = Nothing
    Set categoryYValues = Nothing
End Sub

Private Function IsMissingOrEmpty(v As Variant) As Boolean
    Select Case VarType(v)
        Case vbEmpty
            IsMissingOrEmpty = True
        Case vbString
            IsMissingOrEmpty = (v = "")
        Case Else
            IsMissingOrEmpty = False
    End Select
End Function

Private Function ArrayLength(arr As Variant) As Long
    On Error Resume Next
    ArrayLength = UBound(arr) - LBound(arr) + 1
    If Err.Number <> 0 Then ArrayLength = 0
    On Error GoTo 0
End Function
