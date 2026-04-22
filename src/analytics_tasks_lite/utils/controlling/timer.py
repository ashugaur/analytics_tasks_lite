import time

## timer_start
def timer_start():
    """Record start time."""
    global start_time
    print("⏰ Timer started...")
    # Record the start time
    start_time = time.time()


## timer_end
def timer_end():
    """Calculate overall time taken."""
    global start_time
    try:
        # Record the end time
        end_time = time.time()
        # Calculate the elapsed time
        elapsed_time_seconds = end_time - start_time

        # Extract hours, minutes, seconds, and milliseconds
        hours, remainder = divmod(elapsed_time_seconds, 3600)
        minutes, remainder = divmod(remainder, 60)
        seconds, milliseconds = divmod(remainder, 1)

        # Convert seconds to hours, minutes, and remaining seconds
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)
        milliseconds = int(
            milliseconds * 1000
        )  # convert fractional seconds to milliseconds

        # Print the results
        print(
            f"🔔 Execution Time: {hours} hours {minutes} minutes {seconds} seconds {milliseconds} milliseconds"
        )

        # Release
        del start_time, end_time

    except NameError:
        print("⚠️  WARNING: Please run timer_start function.")
