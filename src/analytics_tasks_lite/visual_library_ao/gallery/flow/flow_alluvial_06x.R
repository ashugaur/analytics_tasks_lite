# %% flow_alluvial_plot_r_plus_sql

#ggalluvial expects data in a long format where:
#alluvium: Identifies each flow (e.g., a unique row or entity in your data).
#x: The stage (e.g., Fill1, Fill2, ..., Fill6).
#stratum: The category at each stage (e.g., 0.8MG, 1.2MG, ..., NoFill).
#y: The count or value for each combination (you'll calculate this).

report_name <- 'flow_alluvial_06x'

# Load required packages
library(tidyr)
library(dplyr)
library(ggplot2)
library(ggalluvial)
library(htmltools)
library(ggtext)
library(clipr)
library(cowplot)
library(patchwork)
library(grid)

# Global variables
chartFontFamily <- "Arial"
chartElementsColor <- "#01387B"
sankeyWidth <- 1000
sankeyHeight <- 800
sankeyMargins <- list(l = 150, r = 150)
heatmapWidth <- 4
heatmapHeight <- 4
heatmapDpi <- 100
sankeyDpi <- 100
flowWidth <- 0.4
textSizeStratum <- 3.0
labelVjust <- 0.5
textSizeStage <- 5
heatmapImgWidth <- 200
heatmapImgHeight <- 200
heatmapHorizontalOffset <- 0
heatmapVerticalOffset <- 0
sort_list <- c("NoFill", "3.0MG", "2.4MG", "1.7MG", "1.2MG", "0.8MG")
stages <- c("Fill1", "Fill2", "Fill3", "Fill4", "Fill5", "Fill6")
category_colors <- c("NoFill" = "#A5A5A5", "0.8MG" = "#8497B0", "1.2MG" = "#0299F4",
                     "1.7MG" = "#2A918B", "2.4MG" = "#8856a7", "3.0MG" = "#d95f0e")

# New parameters for controlling layout
total_plot_width <- 16  # Total width of the final plot in inches
total_plot_height <- 8  # Total height of the final plot in inches
sankey_height_proportion <- 0.75  # Sankey takes 77% of the height
heatmap_height_proportion <- 0.25  # Heatmaps take 23% of the height

# Fixed width and height for heatmaps (in inches) to ensure square shape
heatmap_width_inch <- 2.7  # Fixed width for each heatmap
heatmap_height_inch <- 2.7  # Fixed height for each heatmap to maintain square aspect ratio

# Dictionary for heatmap positions (as a percentage of total plot width)
heatmap_positions <- list(h1 = 0.04, h2 = 0.225, h3 = 0.405, h4 = 0.59, h5 = 0.77)

# Validate the dictionary
if (length(heatmap_positions) != (length(stages) - 1)) {
  stop("The number of heatmap positions must match the number of gaps (stages - 1).")
}
if (!all(sapply(heatmap_positions, function(x) is.numeric(x) && x >= 0 && x <= 1))) {
  stop("All heatmap positions must be numeric values between 0 and 1.")
}

# Import and adjust lodes_data (unchanged)
lodes_data <- read.csv(paste0(vl_, "/flow/lodes_data_06x.csv")) %>%
  mutate(
    y = as.numeric(y),
    x = as.numeric(x),
    stage = factor(stage, levels = stages),
    stratum = factor(stratum, levels = sort_list)
  )

# Import and adjust stratum_totals with threshold
stratum_totals <- read.csv(paste0(vl_, "/flow/stratum_totals_06x.csv")) %>%
  mutate(
    value = as.numeric(value)
  ) %>%
  group_by(stage) %>%
  mutate(
    percentage = round(value / sum(value) * 100, 1),
    label = ifelse(percentage >= 2, # Hide labels below 2%
                   paste0(
                     "<span style='font-size:11pt; text-align:center;'><b>", percentage, "%</b></span><br>",
                     "<span style='font-size:8pt; text-align:center;'>", stratum, "</span>"
                   ),
                   "")
  ) %>%
  ungroup() %>%
  mutate(
    stage = factor(stage, levels = stages),
    stratum = factor(stratum, levels = sort_list)
  ) %>%
  select(stage, stratum, value, label)

# Assuming lodes_data tracks individual patient flows
data <- lodes_data %>%
  group_by(alluvium) %>%
  arrange(x) %>%
  mutate(
    source_stage = stage,
    target_stage = lead(stage),  # Next stage for each patient
    source_cat = stratum,
    target_cat = lead(stratum)   # Next stratum for each patient
  ) %>%
  ungroup() %>%
  filter(!is.na(target_stage)) %>%  # Remove rows where there's no next stage
  group_by(source_stage, target_stage, source_cat, target_cat) %>%
  summarise(value = n(), .groups = "drop")  # Count transitions

# Generate the alluvial plot (Sankey diagram) with adjusted spacing
alluvial_plot <- ggplot() +
  geom_flow(data = lodes_data,
            aes(x = x,
                stratum = stratum,
                alluvium = alluvium,
                y = y,
                fill = stratum),
            stat = "flow",
            width = flowWidth,
            alpha = 0.5) +
  geom_stratum(data = stratum_totals,
               aes(x = stage, y = value, stratum = stratum, fill = stratum),
               width = flowWidth, color = "black", size = 0.1) +
  geom_richtext(
    data = stratum_totals,
    aes(x = stage, y = value, stratum = stratum, label = label),
    stat = "stratum",
    size = textSizeStratum,
    vjust = labelVjust,
    color = chartElementsColor,
    fill = NA,
    label.color = NA
  ) +
  scale_x_discrete(limits = stages, expand = c(0.02, 0.02)) +
  scale_fill_manual(values = category_colors) +
  theme_minimal() +
  theme(
    axis.title.x = element_blank(),
    axis.title.y = element_blank(),
    axis.text.x = element_blank(),
    axis.text.y = element_blank(),
    axis.ticks = element_blank(),
    panel.grid = element_blank(),
    legend.title = element_blank(),
    legend.text = element_text(size = 11, color = chartElementsColor)
  )

# Add stage labels
for (i in seq_along(stages)) {
  alluvial_plot <- alluvial_plot +
    annotate("text", x = i, y = -19.0, label = stages[i], size = textSizeStage, vjust = 1, color = chartElementsColor)
}

# Generate heatmaps as ggplot objects directly
## without the decimal treatment
#heatmap_plots <- list()
#total_patients <- length(unique(lodes_data$alluvium))
#
#for (i in 1:(length(stages)-1)) {
  #heatmap_data <- data %>%
    #filter(source_stage == stages[i], target_stage == stages[i+1]) %>%
    #select(source_cat, target_cat, value)
#
  #if (nrow(heatmap_data) == 0) {
    #cat("Warning: No transitions from", stages[i], "to", stages[i+1], "- skipping heatmap\n")
    #heatmap_plots[[i]] <- NULL
    #next
  #}
#
  #heatmap_data <- heatmap_data %>%
    #mutate(
      #value_percent = round((value / total_patients) * 100),
      #source_cat = gsub("MG", "", source_cat),
      #target_cat = gsub("MG", "", target_cat)
    #)
#
  #heatmap_data_filtered <- heatmap_data %>%
    #filter(source_cat != "NoFill")
#
  #if (nrow(heatmap_data_filtered) == 0) {
    #cat("Warning: No non-'NoFill' transitions from", stages[i], "to", stages[i+1], "- skipping heatmap\n")
    #heatmap_plots[[i]] <- NULL
    #next
  #}
#
  #sort_list_no_nofill <- gsub("MG", "", sort_list[sort_list != "NoFill"])
#
#
  #threshold <- 25
  #heatmap_data_filtered <- heatmap_data_filtered %>%
    #mutate(text_color = ifelse(value > threshold, "white", chartElementsColor))
#
  #min_value <- min(heatmap_data_filtered$value_percent)
  #max_value <- max(heatmap_data_filtered$value_percent)
#
#
  #heatmap_plot <- ggplot(heatmap_data_filtered, aes(x = target_cat, y = source_cat, fill = value_percent)) +
    #geom_tile(color = "white", linewidth = 0.5) +
    #geom_text(aes(label = sprintf("%d", value_percent), color = I(text_color)), size = 4) +
    #scale_x_discrete(limits = gsub("MG", "", sort_list)) +
    #scale_y_discrete(limits = rev(sort_list_no_nofill)) +
    #scale_fill_gradient(
      #low = "#F5E6CC",
      #high = "#1B4F72",
      #breaks = c(min_value, max_value),
      #labels = c(min_value, max_value)
    #) +
    #labs(x = NULL, y = NULL) +
    #coord_fixed(ratio = 1) +  # Enforce a 1:1 aspect ratio for square tiles
    #theme_minimal() +
    #theme(
      #axis.text = element_text(size = 10, family = chartFontFamily, color = chartElementsColor),
      #legend.position = "bottom",
      #legend.direction = "horizontal",
      #legend.title = element_blank(),
      #legend.text = element_text(size = 10, family = chartFontFamily, color = chartElementsColor),
      #legend.box.spacing = unit(0.2, "cm"),
      #panel.grid = element_blank(),
      #plot.background = element_rect(fill = "white", color = NA),
      #panel.background = element_rect(fill = "white", color = NA),
      #legend.justification = "center",
      #legend.box.just = "center",
      #plot.margin = margin(t = 5, r = 5, b = 10, l = 5, unit = "pt"),
      #legend.margin = margin(t = 0, r = 0, b = 0, l = 0),
      #legend.box.margin = margin(t = 0, r = 0, b = 0, l = 0),
      #plot.caption = element_text(hjust = 0.5, size = 12, color = chartElementsColor)
    #) +
    #guides(fill = guide_colourbar(barwidth = 6, barheight = 0.4)) +
    ##labs(title = paste("% titrate, fill", i, "to", i+1))
    #labs(caption = paste("% titrate, fill", i, "to", i+1))
#
  #heatmap_plots[[i]] <- heatmap_plot
#}

# Generate heatmaps as ggplot objects directly
heatmap_plots <- list()
total_patients <- length(unique(lodes_data$alluvium))

for (i in 1:(length(stages)-1)) {
  heatmap_data <- data %>%
    filter(source_stage == stages[i], target_stage == stages[i+1]) %>%
    select(source_cat, target_cat, value)

  if (nrow(heatmap_data) == 0) {
    cat("Warning: No transitions from", stages[i], "to", stages[i+1], "- skipping heatmap\n")
    heatmap_plots[[i]] <- NULL
    next
  }

  heatmap_data <- heatmap_data %>%
    mutate(
      value_percent = (value / total_patients) * 100,  # Keep as numeric, no rounding
      source_cat = gsub("MG", "", source_cat),
      target_cat = gsub("MG", "", target_cat)
    )

  heatmap_data_filtered <- heatmap_data %>%
    filter(source_cat != "NoFill")

  if (nrow(heatmap_data_filtered) == 0) {
    cat("Warning: No non-'NoFill' transitions from", stages[i], "to", stages[i+1], "- skipping heatmap\n")
    heatmap_plots[[i]] <- NULL
    next
  }

  sort_list_no_nofill <- gsub("MG", "", sort_list[sort_list != "NoFill"])

  # Define thresholds and colors
  threshold <- 25
  low_percent_color <- "#CCC5BD"  # Medium gray for < 1%, adjustable
  heatmap_data_filtered <- heatmap_data_filtered %>%
    mutate(text_color = ifelse(value > threshold, "white",
                              ifelse(value_percent < 1, low_percent_color, chartElementsColor)))

  min_value <- min(heatmap_data_filtered$value_percent)
  max_value <- max(heatmap_data_filtered$value_percent)

  heatmap_plot <- ggplot(heatmap_data_filtered, aes(x = target_cat, y = source_cat, fill = value_percent)) +
    geom_tile(color = "white", linewidth = 0.5) +
    geom_text(aes(label = sprintf(ifelse(value_percent < 1, "%.1f", "%.0f"), value_percent),
                  color = I(text_color)), size = 4) +
    scale_x_discrete(limits = gsub("MG", "", sort_list)) +
    scale_y_discrete(limits = rev(sort_list_no_nofill)) +
    scale_fill_gradient(
      low = "#F5E6CC",
      high = "#1B4F72",
      breaks = c(min_value, max_value),
      labels = c(min_value, max_value)
    ) +
    labs(x = NULL, y = NULL) +
    coord_fixed(ratio = 1) +
    theme_minimal() +
    theme(
      axis.text = element_text(size = 10, family = chartFontFamily, color = chartElementsColor),
      legend.position = "bottom",
      legend.direction = "horizontal",
      legend.title = element_blank(),
      legend.text = element_text(size = 10, family = chartFontFamily, color = chartElementsColor),
      legend.box.spacing = unit(0.2, "cm"),
      panel.grid = element_blank(),
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      legend.justification = "center",
      legend.box.just = "center",
      plot.margin = margin(t = 5, r = 5, b = 10, l = 5, unit = "pt"),
      legend.margin = margin(t = 0, r = 0, b = 0, l = 0),
      legend.box.margin = margin(t = 0, r = 0, b = 0, l = 0),
      plot.caption = element_text(hjust = 0.5, size = 12, color = chartElementsColor)
    ) +
    guides(fill = guide_colourbar(barwidth = 6, barheight = 0.4)) +
    labs(caption = paste("% titrate, fill", i, "to", i+1))

  heatmap_plots[[i]] <- heatmap_plot
}

# Filter out NULL elements from heatmap_plots
valid_heatmap_plots <- Filter(Negate(is.null), heatmap_plots)

# Convert percentage positions to inches based on total plot width
heatmap_positions_inch <- sapply(heatmap_positions, function(x) x * total_plot_width)

# Create a new layout for the heatmaps with spacers to position them at the specified locations
heatmap_layout <- list()
heatmap_widths <- c()

# Keep track of the current position in inches
current_position <- 0

for (i in 1:(length(stages) - 1)) {
  # Target position for the current heatmap
  target_position <- heatmap_positions_inch[[i]]

  # Add a spacer to reach the target position
  spacer_width <- target_position - current_position
  if (spacer_width < 0) {
    stop("Heatmap positions must be in increasing order.")
  }

  # Add the spacer (if width > 0)
  if (spacer_width > 0) {
    heatmap_layout <- c(heatmap_layout, list(plot_spacer()))
    heatmap_widths <- c(heatmap_widths, spacer_width)
  }

  # Add the heatmap
  if (i %in% which(!sapply(heatmap_plots, is.null))) {
    heatmap_layout <- c(heatmap_layout, list(heatmap_plots[[which(which(!sapply(heatmap_plots, is.null)) == i)]]))
  } else {
    heatmap_layout <- c(heatmap_layout, list(plot_spacer()))
  }
  heatmap_widths <- c(heatmap_widths, heatmap_width_inch)  # Fixed width for the heatmap

  # Update the current position
  current_position <- current_position + spacer_width + heatmap_width_inch
}

# If there's remaining space at the end, add a final spacer
if (current_position < total_plot_width) {
  heatmap_layout <- c(heatmap_layout, list(plot_spacer()))
  heatmap_widths <- c(heatmap_widths, total_plot_width - current_position)
}

# Combine the heatmaps into a row with the new widths
heatmap_row <- wrap_plots(heatmap_layout, ncol = length(heatmap_layout), widths = heatmap_widths)

# Combine the alluvial plot and heatmap row with specified height proportions
combined_plot <- alluvial_plot / heatmap_row +
  plot_layout(heights = c(sankey_height_proportion, heatmap_height_proportion))

# Save the combined plot as a single high-quality image
ggsave(
  filename = paste0(report_name, ".png"),
  plot = combined_plot,
  width = total_plot_width,
  height = total_plot_height,
  dpi = sankeyDpi,
  units = "in"
)

# Optionally, open the file
browseURL(paste0(report_name, ".png"))

#source(paste0(vl_, "/flow/flow_alluvial_6x.R"))

