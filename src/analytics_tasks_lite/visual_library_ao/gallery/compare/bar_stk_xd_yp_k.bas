Sub bar_stk_xd_yp_k()
    Dim ws As Worksheet
    Dim chartObj As ChartObject
    Dim chart As chart
    Dim lastRow As Long
    Dim i As Long, j As Long
    Dim uniqueMonths As Object
    Dim uniqueCategories As Object
    Dim monthCategories As Object
    Dim outputCol As Long
    Dim outputRow As Long
    Dim colorMap As Object
    Dim totalValue As Double
    Dim percentageStartRow As Long

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
    legend_visible = False
    y_axis_unit = 20000
    total_format = "[>=1000]#,##0,K;[>=1]0.0,K"
    bar_width = 100
    label_format = "0%" '"0.0%";
    chart_width = 760
    chart_height = 280
    hideLabel = 0.01 ' Hide labels below certain %

    chartTitle = " "
    xAxisTitle = ""
    yAxisTitle = ""

    ' Define the sorting array (can be "" for default sorting)
    sort_array = Array("New", "Old", "Mature")  ' Fixed: proper category sorting

    '#--------------------------------------------------------------------------
    '#··· Calibration end                                                    ···
    '#--------------------------------------------------------------------------

    ' Set active sheet
    Set ws = ActiveSheet

    ' Find last row of data
    lastRow = ws.Cells(Rows.Count, 1).End(xlUp).Row

    ' Create dictionaries for unique months, categories, and color mapping
    Set uniqueMonths = CreateObject("Scripting.Dictionary")
    Set uniqueCategories = CreateObject("Scripting.Dictionary")
    Set colorMap = CreateObject("Scripting.Dictionary")
    Set monthCategories = CreateObject("Scripting.Dictionary")

    ' Collect unique months and categories, and store color mappings
    For i = 2 To lastRow
        Dim monthKey As Variant
        Dim categoryKey As Variant
        
        ' Fixed: Better date handling to ensure consistent month format
        Dim cellDate As Date
        On Error Resume Next
        cellDate = CDate(ws.Cells(i, 1).value)
        If Err.Number <> 0 Then
            ' If direct conversion fails, try parsing as text
            cellDate = DateValue(ws.Cells(i, 1).value)
        End If
        On Error GoTo 0
        
        monthKey = Format(cellDate, "mmm-yy")
        categoryKey = Trim(ws.Cells(i, 2).value) ' Category in Column B - added Trim

        If Not uniqueMonths.Exists(monthKey) Then uniqueMonths.Add monthKey, 0
        If Not uniqueCategories.Exists(categoryKey) Then uniqueCategories.Add categoryKey, 0

        ' Fixed: Better RGB parsing
        Dim rgbText As String
        Dim rgbValues As Variant
        Dim rgbColor As Long
        rgbText = Trim(ws.Cells(i, 5).value)
        
        ' Handle both formats: "56, 194, 140" or "(56, 194, 140)"
        rgbText = Replace(rgbText, "(", "")
        rgbText = Replace(rgbText, ")", "")
        rgbText = Replace(rgbText, " ", "") ' Remove all spaces
        rgbValues = Split(rgbText, ",")

        If UBound(rgbValues) >= 2 Then
            rgbColor = RGB(CInt(rgbValues(0)), CInt(rgbValues(1)), CInt(rgbValues(2)))
            If Not colorMap.Exists(categoryKey) Then colorMap.Add categoryKey, rgbColor
        Else
            If Not colorMap.Exists(categoryKey) Then colorMap.Add categoryKey, RGB(128, 128, 128) ' Default gray
        End If

        Dim monthCategoryKey As String
        monthCategoryKey = monthKey & "|" & categoryKey
        If Not monthCategories.Exists(monthCategoryKey) Then
            monthCategories.Add monthCategoryKey, ws.Cells(i, 3).value
        Else
            monthCategories(monthCategoryKey) = monthCategories(monthCategoryKey) + ws.Cells(i, 3).value
        End If
    Next i

    ' Debug: Check if we have data
    If uniqueMonths.Count = 0 Or uniqueCategories.Count = 0 Then
        MsgBox "No data found! Check your data format and range."
        Exit Sub
    End If

    ' Transpose data to wide format starting from column O (15)
    outputCol = 15 ' Start at column O
    outputRow = 1  ' Header row for categories

    ' Write month headers (dates) starting from column P (outputCol + 1)
    ws.Cells(outputRow, outputCol).value = "Date"
    
    ' Sort months chronologically
    Dim monthKeys As Variant
    monthKeys = uniqueMonths.keys
    
    ' Simple bubble sort for months (you could implement a more sophisticated sort)
    Dim k As Long, l As Long, temp As Variant
    For k = LBound(monthKeys) To UBound(monthKeys) - 1
        For l = k + 1 To UBound(monthKeys)
            Dim date1 As Date, date2 As Date
            date1 = DateValue("01-" & monthKeys(k))
            date2 = DateValue("01-" & monthKeys(l))
            If date1 > date2 Then
                temp = monthKeys(k)
                monthKeys(k) = monthKeys(l)
                monthKeys(l) = temp
            End If
        Next l
    Next k
    
    j = 0
    For k = LBound(monthKeys) To UBound(monthKeys)
        j = j + 1
        Dim properDate As Date
        Dim monthName As String
        Dim yearPart As String
        monthName = Left(monthKeys(k), 3)
        yearPart = Right(monthKeys(k), 2)
        properDate = DateSerial(2000 + CInt(yearPart), Month(DateValue("01-" & monthName & "-2022")), 1)
        ws.Cells(outputRow, outputCol + j).value = properDate
        ws.Cells(outputRow, outputCol + j).NumberFormat = "mmm-yy"
    Next k

    ' Sort categories based on sort_array or ascending order
    Dim sortedCategories As Variant
    Dim useDefaultSort As Boolean
    useDefaultSort = False
    
    ' Check if we should use default sorting
    If IsMissingOrEmpty(sort_array) Then
        useDefaultSort = True
    ElseIf IsArray(sort_array) Then
        If ArrayLength(sort_array) = 0 Then
            useDefaultSort = True
        ElseIf UBound(sort_array) = 0 Then
            On Error Resume Next
            If Trim(CStr(sort_array(0))) = "" Or Trim(CStr(sort_array(0))) = " " Then
                useDefaultSort = True
            End If
            On Error GoTo 0
        End If
    Else
        useDefaultSort = True
    End If
    
    If useDefaultSort Then
        ' Default sorting: ascending order of category names
        sortedCategories = uniqueCategories.keys
        For k = LBound(sortedCategories) To UBound(sortedCategories) - 1
            For l = k + 1 To UBound(sortedCategories)
                If sortedCategories(k) > sortedCategories(l) Then
                    temp = sortedCategories(k)
                    sortedCategories(k) = sortedCategories(l)
                    sortedCategories(l) = temp
                End If
            Next l
        Next k
    Else
        ' Custom sorting based on sort_array - only include categories that exist
        ReDim sortedCategories(0 To uniqueCategories.Count - 1)
        Dim sortIndex As Long
        sortIndex = 0
        
        ' First, add categories in the order specified by sort_array
        For k = LBound(sort_array) To UBound(sort_array)
            If uniqueCategories.Exists(sort_array(k)) Then
                sortedCategories(sortIndex) = sort_array(k)
                sortIndex = sortIndex + 1
            End If
        Next k
        
        ' Then add any remaining categories not in sort_array
        For Each categoryKey In uniqueCategories.keys
            Dim found As Boolean
            found = False
            For k = LBound(sort_array) To UBound(sort_array)
                If sort_array(k) = categoryKey Then
                    found = True
                    Exit For
                End If
            Next k
            If Not found Then
                sortedCategories(sortIndex) = categoryKey
                sortIndex = sortIndex + 1
            End If
        Next categoryKey
        
        ' Resize array to actual size
        ReDim Preserve sortedCategories(0 To sortIndex - 1)
    End If

    ' Write category headers and values based on sorted order
    outputRow = 2
    For k = LBound(sortedCategories) To UBound(sortedCategories)
        categoryKey = sortedCategories(k)
        If uniqueCategories.Exists(categoryKey) Then ' Ensure category exists in data
            ws.Cells(outputRow, outputCol).value = categoryKey
            j = 0
            For l = LBound(monthKeys) To UBound(monthKeys)
                j = j + 1
                Dim fullKey As String
                fullKey = monthKeys(l) & "|" & categoryKey
                If monthCategories.Exists(fullKey) Then
                    ws.Cells(outputRow, outputCol + j).value = monthCategories(fullKey)
                Else
                    ws.Cells(outputRow, outputCol + j).value = 0
                End If
            Next l
            outputRow = outputRow + 1
        End If
    Next k

    ' Add a row for totals below the categories
    ws.Cells(outputRow, outputCol).value = "Total"
    For j = 1 To UBound(monthKeys) - LBound(monthKeys) + 1
        totalValue = 0
        For i = 2 To outputRow - 1
            totalValue = totalValue + ws.Cells(i, outputCol + j).value
        Next i
        ws.Cells(outputRow, outputCol + j).value = totalValue
    Next j

    ' Store the total row number for reference
    Dim totalRow As Long
    totalRow = outputRow

    ' Calculate percentage values (5 rows below the totals)
    percentageStartRow = totalRow + 5

    ' Add header row for percentages
    ws.Cells(percentageStartRow - 1, outputCol).value = "Percentage Values"

    ' Manually transfer the column headers
    Dim monthCount As Long
    monthCount = UBound(monthKeys) - LBound(monthKeys) + 1

    ' Copy headers without using the Copy method
    For colIdx = 0 To monthCount
        ws.Cells(percentageStartRow, outputCol + colIdx).value = ws.Cells(1, outputCol + colIdx).value
        ws.Cells(percentageStartRow, outputCol + colIdx).NumberFormat = ws.Cells(1, outputCol + colIdx).NumberFormat
    Next colIdx

    ' Calculate percentages for each category
    For i = 2 To totalRow - 1
        ws.Cells(percentageStartRow + i - 1, outputCol).value = ws.Cells(i, outputCol).value

        For j = 1 To monthCount
            ' Only calculate percentage if total is not zero
            If ws.Cells(totalRow, outputCol + j).value <> 0 Then
                ws.Cells(percentageStartRow + i - 1, outputCol + j).value = _
                    ws.Cells(i, outputCol + j).value / ws.Cells(totalRow, outputCol + j).value
            Else
                ws.Cells(percentageStartRow + i - 1, outputCol + j).value = 0
            End If
            ' Format as percentage
            ws.Cells(percentageStartRow + i - 1, outputCol + j).NumberFormat = "0.0%"
        Next j
    Next i

    ' Remove any existing charts
    For Each chartObj In ws.ChartObjects
        chartObj.Delete
    Next chartObj

    ' Create chart object
    Set chartObj = ws.ChartObjects.Add(Left:=200, Width:=chart_width, Top:=50, Height:=chart_height)
    Set chart = chartObj.chart

    chart.ChartType = xlColumnStacked
    chart.ChartArea.Font.Name = chartFontFamily
    chart.ChartArea.Font.Color = chartElementsColor
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
        chart.chartTitle.Font.Color = chartElementsColor
    Else
        chart.HasTitle = False
    End If

    ' Increase space between the chart title and the chart
    With chart
        ' Move the plot area down by increasing its Top property
        .PlotArea.Top = .PlotArea.Top + 20 ' Adjust 20 as needed
    End With

    ' Set up the source data using the PERCENTAGE values
    Dim percentDataRange As Range
    Set percentDataRange = ws.Range(ws.Cells(percentageStartRow + 1, outputCol), _
                                   ws.Cells(percentageStartRow + totalRow - 2, outputCol + monthCount))
    chart.SetSourceData Source:=percentDataRange

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
        .TickLabels.NumberFormat = "mmm-yy"
        Dim categoryLabels As Range
        Set categoryLabels = ws.Range(ws.Cells(1, outputCol + 1), ws.Cells(1, outputCol + monthCount))
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

    ' Apply colors and data labels to series (percentage format)
    Dim seriesIndex As Long
    For seriesIndex = 1 To chart.SeriesCollection.Count
        Dim seriesName As String
        seriesName = chart.SeriesCollection(seriesIndex).Name
        With chart.SeriesCollection(seriesIndex)
            If colorMap.Exists(seriesName) Then
                .Format.Fill.ForeColor.RGB = colorMap(seriesName)
            Else
                .Format.Fill.ForeColor.RGB = RGB(128, 128, 128) ' Default gray instead of black
            End If
            .HasDataLabels = True

            ' Hide data labels below the threshold for each point
            Dim pointIdx As Long
            For pointIdx = 1 To .Points.Count
                ' Get the value of this specific data point
                Dim pointValue As Double
                ' Calculate the correct row and column from percentageStartRow area
                Dim dataRow As Long, dataCol As Long
                dataRow = percentageStartRow + seriesIndex
                dataCol = outputCol + pointIdx

                ' Make sure we're reading from the right place in the percentage table
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
                        .Font.Color = RGB(255, 255, 255)
                        .NumberFormat = label_format
                    End With
                End If
            Next pointIdx
        End With
    Next seriesIndex

    On Error Resume Next
    For seriesIndex = 1 To chart.SeriesCollection.Count - 1
        Dim categoryName As String
        categoryName = ws.Cells(percentageStartRow + seriesIndex, outputCol).value
        If Len(Trim(categoryName)) > 0 Then
            chart.SeriesCollection(seriesIndex).Name = categoryName
        End If
    Next seriesIndex
    On Error GoTo 0

    ' Add total values as a line series (absolute numbers)
    Dim totalSeries As series
    Set totalSeries = chart.SeriesCollection.NewSeries
    With totalSeries
        .Name = "Total"
        .Values = ws.Range(ws.Cells(totalRow, outputCol + 1), ws.Cells(totalRow, outputCol + monthCount))
        .ChartType = xlLine
        .Format.Line.Visible = msoFalse  ' Make the line invisible
        .MarkerStyle = xlMarkerStyleNone ' Remove markers
        .HasDataLabels = True
        With .DataLabels
            .ShowValue = True
            .Position = xlLabelPositionAbove
            .Font.Name = chartFontFamily
            .Font.Size = series_label_font_size
            .Font.Bold = False            ' Make labels bold to stand out
            .Font.Color = chartElementsColor
            .NumberFormat = total_format      ' Format as number with thousand separators
        End With
    End With

    ' Create a secondary axis for the Total line series
    totalSeries.AxisGroup = xlSecondary

    With chart.Axes(xlValue, xlSecondary)
        .Border.LineStyle = xlLineNone ' Hide the axis line
        .MajorTickMark = xlTickMarkNone ' Hide major tick marks
        .MinorTickMark = xlTickMarkNone ' Hide minor tick marks
        .TickLabels.Font.Color = RGB(255, 255, 255) ' Hide tick labels by making them white
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
    For j = 1 To monthCount
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
                .Font.Color = chartElementsColor
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

    ' Debug output
    Debug.Print "Months found: " & uniqueMonths.Count
    Debug.Print "Categories found: " & uniqueCategories.Count
    Debug.Print "Data range created from row " & percentageStartRow + 1 & " to " & percentageStartRow + totalRow - 2

    Set ws = Nothing
    Set chartObj = Nothing
    Set chart = Nothing
    Set uniqueMonths = Nothing
    Set uniqueCategories = Nothing
    Set colorMap = Nothing
    Set monthCategories = Nothing
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

