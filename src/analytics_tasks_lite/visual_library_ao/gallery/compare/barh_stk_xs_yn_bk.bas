Sub barh_stk_xs_yn_bk()
    Dim ws As Worksheet
    Dim chartObj As ChartObject
    Dim chart As chart
    Dim lastRow As Long
    Dim i As Long
    

    '#--------------------------------------------------------------------------
    '#··· Calibration start                                                  ···
    '#--------------------------------------------------------------------------

    Dim studyPeriod As Integer
    studyPeriod = 12 ' Set your study period here (12, 24, etc.)
    
    ' Chart styling variables
    Dim chartFontFamily As String
    Dim chartElementsColor As Long
    Dim remainingColor As Long
    Dim chart_title_font_size As String
    Dim xtick_label_font_size As Integer
    Dim ytick_label_font_size As Integer
    Dim series_label_font_size As Integer
    Dim legend_font_size As Integer
    Dim chart_width As Integer
    Dim chart_height As Integer
    
    ' Title variable
    Dim chartTitle As String
    
    ' Set the font family, size and colors
    chartFontFamily = "Calibri"
    chartElementsColor = RGB(0, 22, 94) ' Dark blue for chart elements
    remainingColor = RGB(220, 220, 220) ' Light gray for remaining time
    chart_title_font_size = 12 ' Default
    xtick_label_font_size = 9 ' Default
    ytick_label_font_size = 9 ' Default
    series_label_font_size = 8 ' Default
    legend_font_size = 9 ' Default
    chart_width = 260
    chart_height = 35
    
    ' Set the chart title with dynamic period
    chartTitle = "bar_horizontal_xstr_ynum_bespoke : " & studyPeriod & " months"

    '#--------------------------------------------------------------------------
    '#··· Calibration end                                                    ···
    '#--------------------------------------------------------------------------

    ' Set the worksheet containing data
    Set ws = ActiveSheet
    
    Dim existingChart As ChartObject
    For Each existingChart In ws.ChartObjects
        existingChart.Delete
    Next existingChart
    
    ' Find the last row of data in column A
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    
    ' Use column F for remaining values
    ws.Cells(1, 6).value = "Remaining"
    For i = 2 To lastRow
        Dim value As Double
        value = CDbl(ws.Cells(i, 3).value)
        ws.Cells(i, 6).value = studyPeriod - value ' Calculate remaining months in column F
    Next i
    
    ' Add a chart object (position and size as needed)
    Set chartObj = ws.ChartObjects.Add(Left:=200, Width:=chart_width, Top:=50, Height:=chart_height * (lastRow - 1))
    Set chart = chartObj.chart
    
    ' Set chart type to horizontal stacked bar
    chart.ChartType = xlBarStacked
    chart.ChartArea.Font.Name = chartFontFamily
    chart.ChartArea.Font.Color = chartElementsColor
    chart.ChartArea.Border.LineStyle = xlNone
    chart.ChartArea.Format.Fill.ForeColor.RGB = RGB(255, 255, 255)
    
    ' Set chart title
    chart.HasTitle = True
    chart.chartTitle.Text = chartTitle
    chart.chartTitle.Font.Size = chart_title_font_size
    chart.chartTitle.Font.Name = chartFontFamily
    chart.chartTitle.Font.Color = chartElementsColor
    chart.chartTitle.Font.Bold = True
    chart.chartTitle.Format.TextFrame2.TextRange.ParagraphFormat.Alignment = msoAlignLeft
    chart.chartTitle.Left = 0
    
    ' No legend
    chart.HasLegend = False
    
    ' Clear any existing series
    Do While chart.SeriesCollection.Count > 0
        chart.SeriesCollection(1).Delete
    Loop
    
    ' Add the actual values series
    Dim valuesSeries As series
    Set valuesSeries = chart.SeriesCollection.NewSeries
    valuesSeries.Name = "Actual"
    valuesSeries.Values = ws.Range("C2:C" & lastRow)
    valuesSeries.XValues = ws.Range("A2:A" & lastRow)
    
    ' Add the remaining values series
    Dim remainingSeries As series
    Set remainingSeries = chart.SeriesCollection.NewSeries
    remainingSeries.Name = "Remaining"
    remainingSeries.Values = ws.Range("F2:F" & lastRow) ' Use column F
    remainingSeries.XValues = ws.Range("A2:A" & lastRow)
    
    ' Format the remaining series (gray bars)
    remainingSeries.Format.Fill.ForeColor.RGB = remainingColor
    remainingSeries.HasDataLabels = False
    
    ' Format the actual values series and add data labels
    valuesSeries.HasDataLabels = True
    With valuesSeries.DataLabels
        .Position = xlLabelPositionCenter
        .Font.Bold = True
        .Font.Size = series_label_font_size
        .Font.Name = chartFontFamily
        .Font.Color = RGB(255, 255, 255) ' White text for contrast
        .NumberFormat = "0 ""months"""  ' Format labels to show "months"
    End With
    
    ' Apply individual colors to each bar in the actual values series
    For i = 1 To valuesSeries.Points.Count
        Dim colorRGBStr As String
        Dim rgbValues() As String
        Dim r As Long, g As Long, b As Long
        
        ' Get the RGB values from column E (color_rgb)
        colorRGBStr = Trim(ws.Cells(i + 1, 5).value)
        
        ' Check if it’s an RGB string
        If InStr(colorRGBStr, ",") > 0 Then
            rgbValues = Split(colorRGBStr, ",")
            r = CLng(Trim(rgbValues(0)))
            g = CLng(Trim(rgbValues(1)))
            b = CLng(Trim(rgbValues(2)))
        Else
            ' Fall back to hex value from column D
            Dim hexColor As String
            hexColor = Trim(ws.Cells(i + 1, 4).value)
            If Left(hexColor, 1) = "#" Then hexColor = Mid(hexColor, 2)
            r = CLng("&H" & Mid(hexColor, 1, 2))
            g = CLng("&H" & Mid(hexColor, 3, 2))
            b = CLng("&H" & Mid(hexColor, 5, 2))
        End If
        
        ' Set the color for the bar
        valuesSeries.Points(i).Format.Fill.ForeColor.RGB = RGB(r, g, b)
    Next i
    
    ' Format category (X) axis
    With chart.Axes(xlCategory)
        .HasTitle = False
        .TickLabels.Font.Size = xtick_label_font_size
        .TickLabels.Font.Name = chartFontFamily
        .TickLabels.Font.Color = chartElementsColor ' Uniform dark blue
        .MajorTickMark = xlNone
        .MinorTickMark = xlNone
        .Border.LineStyle = xlNone
        .TickLabelPosition = xlTickLabelPositionLow
    End With
    
    ' Format value (Y) axis
    With chart.Axes(xlValue)
        .HasTitle = False
        .MajorTickMark = xlNone
        .MinorTickMark = xlNone
        .MajorGridlines.Delete
        .Border.LineStyle = xlNone
        .MinimumScale = 0
        .MaximumScale = studyPeriod
        .TickLabels.NumberFormat = "General"
        .TickLabelPosition = xlNone
    End With
    
    ' Remove plot area border
    chart.PlotArea.Border.LineStyle = xlNone
    chart.PlotArea.Format.Fill.Visible = msoFalse
    
    ' Set small gap width
    chart.ChartGroups(1).GapWidth = 20
    
    ' Clean up
    Set ws = Nothing
    Set chartObj = Nothing
    Set chart = Nothing
    Set valuesSeries = Nothing
    Set remainingSeries = Nothing
End Sub