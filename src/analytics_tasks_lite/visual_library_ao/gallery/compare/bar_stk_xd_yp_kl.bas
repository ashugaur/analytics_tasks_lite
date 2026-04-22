Sub bar_stk_xd_yp_kl()
    Dim ws As Worksheet
    Dim chartObj As ChartObject
    Dim chart As chart
    Dim lastRow As Long
    Dim i As Long
    Dim uniqueCategories As Object
    Dim colorMap As Object
    
    ' Chart styling variables
    Dim chartFontFamily As String
    Dim chartElementsColor As Long
    Dim legend_font_size As Integer
    Dim chart_width As Integer
    Dim chart_height As Integer
    
    ' Sorting array
    Dim sort_array As Variant
    
    ' Set the font family, size, and colors
    chartFontFamily = "Arial"
    chartElementsColor = RGB(0, 22, 94)
    legend_font_size = 10
    chart_width = 800  ' Initial width for legend-only
    chart_height = 100 ' Initial height for legend-only
    
    ' Define the sorting array (can be "" for default sorting)
    sort_array = Array("New", "Old", "Mature") ' Modified to match your categories
    
    ' Set active sheet
    Set ws = ActiveSheet
    
    ' Find last row of data
    lastRow = ws.Cells(Rows.count, 1).End(xlUp).Row
    
    ' Create dictionaries for unique categories and color mapping
    Set uniqueCategories = CreateObject("Scripting.Dictionary")
    Set colorMap = CreateObject("Scripting.Dictionary")
    
    ' Collect unique categories and their colors
    For i = 2 To lastRow
        Dim categoryKey As String
        categoryKey = ws.Cells(i, 2).value ' Category in Column B (New, Old, Mature)
        
        If Not uniqueCategories.Exists(categoryKey) Then
            uniqueCategories.Add categoryKey, 0
            
            ' Parse RGB color from Column E (assuming format "R, G, B")
            Dim rgbText As String
            Dim rgbValues As Variant
            Dim rgbColor As Long
            rgbText = ws.Cells(i, 5).value
            ' Remove any parentheses if present
            rgbText = Replace(rgbText, "(", "")
            rgbText = Replace(rgbText, ")", "")
            ' Split by comma (your data shows comma-space format)
            rgbValues = Split(rgbText, ", ")
            
            If UBound(rgbValues) >= 2 Then
                rgbColor = RGB(CInt(Trim(rgbValues(0))), CInt(Trim(rgbValues(1))), CInt(Trim(rgbValues(2))))
                colorMap.Add categoryKey, rgbColor
            Else
                ' Try splitting by comma only if comma+space didn't work
                rgbValues = Split(rgbText, ",")
                If UBound(rgbValues) >= 2 Then
                    rgbColor = RGB(CInt(Trim(rgbValues(0))), CInt(Trim(rgbValues(1))), CInt(Trim(rgbValues(2))))
                    colorMap.Add categoryKey, rgbColor
                Else
                    colorMap.Add categoryKey, RGB(0, 0, 0) ' Default to black if invalid
                End If
            End If
        End If
    Next i
    
    ' Sort categories based on sort_array or ascending order
    Dim sortedCategories As Variant
    If IsMissingOrEmpty(sort_array) Or (IsArray(sort_array) And ArrayLength(sort_array) = 0) Then
        ' Default sorting: ascending order of category names
        sortedCategories = uniqueCategories.keys
        Dim temp As Variant, k As Long, l As Long
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
        ' Custom sorting based on sort_array
        sortedCategories = sort_array
    End If
    
    ' Remove any existing charts
    For Each chartObj In ws.ChartObjects
        chartObj.Delete
    Next chartObj
    
    ' Create a dummy chart object to hold the legend
    Set chartObj = ws.ChartObjects.Add(Left:=200, Width:=chart_width, Top:=50, Height:=chart_height)
    Set chart = chartObj.chart
    
    ' Use a bar chart type as a base (to match original stacked bar style)
    chart.ChartType = xlColumnStacked
    
    ' Add a dummy series to populate the legend with visible color keys
    Dim keyIndex As Long
    For keyIndex = LBound(sortedCategories) To UBound(sortedCategories)
        Dim currentCategory As String
        currentCategory = sortedCategories(keyIndex)
        If uniqueCategories.Exists(currentCategory) Then ' Ensure category exists in data
            With chart.SeriesCollection.NewSeries
                .Name = currentCategory
                .Values = Array(1) ' Small value instead of 0 to avoid issues
                .xValues = Array("Dummy") ' Dummy category name
                If colorMap.Exists(currentCategory) Then
                    .Format.Fill.ForeColor.RGB = colorMap(currentCategory) ' Set color for legend key
                    .Format.Fill.Transparency = 0 ' Ensure color is visible in legend
                End If
                .HasDataLabels = False ' No data labels
                .Border.LineStyle = xlNone ' No border on bars
            End With
        End If
    Next keyIndex
    
    ' Configure the chart to show only the legend
    With chart
        .HasTitle = False
        
        ' Remove axes if they exist
        On Error Resume Next ' Ignore errors if axes don't exist
        .Axes(xlCategory).Delete ' Remove X-axis
        .Axes(xlValue).Delete    ' Remove Y-axis
        On Error GoTo 0
        
        .ChartArea.Border.LineStyle = xlLineStyleNone ' No border
        
        ' Configure and position the legend
        With .Legend
            .Position = xlLegendPositionTop
            .Left = 0
            .Top = 0
            .Font.Name = chartFontFamily
            .Font.Size = legend_font_size
            .Font.color = chartElementsColor
            .Border.LineStyle = xlLineStyleNone ' No border around legend
            .IncludeInLayout = True ' Ensure legend is part of chart layout
        End With
        
        ' Make plot area invisible
        With .PlotArea
            .Format.Fill.Visible = msoFalse
            .Format.Line.Visible = msoFalse
            .Left = 0
            .Top = 0
            .Width = 0
            .Height = 0
        End With
        
        ' Resize chart to fit legend only
        chartObj.Width = .Legend.Width + 20
        chartObj.Height = .Legend.Height + 20
    End With
    
    ' Clean up
    Set ws = Nothing
    Set chartObj = Nothing
    Set chart = Nothing
    Set uniqueCategories = Nothing
    Set colorMap = Nothing
    
    'MsgBox "Legend created successfully!", vbInformation
End Sub

' Helper functions from original code
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
