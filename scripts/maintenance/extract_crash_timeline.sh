#!/usr/bin/env bash
# Extract crash timeline from syslog files
# Usage: ./extract_crash_timeline.sh --service "cohezion-surreal" --from "2026-02-10" --to "2026-02-18"

set -euo pipefail

# Default values
SERVICE=""
FROM_DATE=""
TO_DATE=""
OUTPUT_DIR="data/archives"
SYSLOG_DIR="/var/log"

# Parse command-line arguments
show_usage() {
    cat <<EOF
Usage: $0 --service SERVICE --from FROM_DATE --to TO_DATE [OPTIONS]

Extract crash timeline from syslog files and create structured report.

Required arguments:
  --service SERVICE     Service name to search for (e.g., "cohezion-surreal")
  --from FROM_DATE      Start date in YYYY-MM-DD format
  --to TO_DATE          End date in YYYY-MM-DD format

Optional arguments:
  --output-dir DIR      Output directory (default: data/archives)
  --syslog-dir DIR      Syslog directory (default: /var/log)
  --help                Show this help message

Examples:
  $0 --service "cohezion-surreal" --from "2026-02-10" --to "2026-02-18"
  $0 --service "systemd" --from "2026-02-01" --to "2026-02-10" --output-dir /tmp/archives
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --from)
            FROM_DATE="$2"
            shift 2
            ;;
        --to)
            TO_DATE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --syslog-dir)
            SYSLOG_DIR="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            show_usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$SERVICE" || -z "$FROM_DATE" || -z "$TO_DATE" ]]; then
    echo "Error: Missing required arguments" >&2
    show_usage
    exit 1
fi

# Validate date format (basic check)
if ! [[ "$FROM_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || ! [[ "$TO_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Error: Dates must be in YYYY-MM-DD format" >&2
    exit 1
fi

# Create output directory
INCIDENT_SLUG=$(echo "$FROM_DATE" | cut -d- -f1-2)-crash-loop
ARCHIVE_DIR="$OUTPUT_DIR/$INCIDENT_SLUG"
mkdir -p "$ARCHIVE_DIR"

TIMELINE_FILE="$ARCHIVE_DIR/timeline.md"
RAW_ARCHIVE="$ARCHIVE_DIR/raw-crash-events.log"
COMPRESSED_ARCHIVE="${RAW_ARCHIVE}.zst"
TEMP_EVENTS=$(mktemp /tmp/crash_events.XXXXXX)
UNIQUE_EVENTS=$(mktemp /tmp/unique_events.XXXXXX)
DAILY_COUNTS=$(mktemp /tmp/daily_counts.XXXXXX)

echo "Extracting crash timeline for $SERVICE from $FROM_DATE to $TO_DATE..."
echo "Output directory: $ARCHIVE_DIR"

# Function to search log files (handles both plain and gzipped)
search_logs() {
    local pattern="$1"
    local file="$2"

    if [[ "$file" == *.gz ]]; then
        zgrep -E "$pattern" "$file" 2>/dev/null || true
    else
        grep -E "$pattern" "$file" 2>/dev/null || true
    fi
}

# Extract events from syslog and rotated files
echo "Searching for $SERVICE events in syslog files..."
> "$TEMP_EVENTS"

# Search all syslog files (current and rotated)
for syslog in "$SYSLOG_DIR"/syslog "$SYSLOG_DIR"/syslog.[0-9]* "$SYSLOG_DIR"/syslog.[0-9]*.gz; do
    if [[ -f "$syslog" ]]; then
        echo "  Processing: $syslog"
        # Extract lines matching service name, date range, and crash-related keywords
        search_logs "$SERVICE" "$syslog" | \
            awk -v from="$FROM_DATE" -v to="$TO_DATE" '
                {
                    # Extract date from RFC 3339 timestamp (format: 2026-02-15T00:00:01.835776-05:00)
                    # First field should be the timestamp
                    timestamp = $1
                    # Extract YYYY-MM-DD from timestamp (first 10 characters)
                    if (length(timestamp) >= 10 && substr(timestamp, 5, 1) == "-" && substr(timestamp, 8, 1) == "-") {
                        current_date = substr(timestamp, 1, 10)

                        # Filter by date range
                        if (current_date >= from && current_date <= to) {
                            print
                        }
                    }
                }
            ' >> "$TEMP_EVENTS"
    fi
done

if [[ ! -s "$TEMP_EVENTS" ]]; then
    echo "Warning: No events found for $SERVICE in date range $FROM_DATE to $TO_DATE"
    rm -f "$TEMP_EVENTS" "$UNIQUE_EVENTS" "$DAILY_COUNTS"
    exit 0
fi

EVENT_COUNT=$(wc -l < "$TEMP_EVENTS")
echo "Found $EVENT_COUNT total events"

# Deduplicate events while preserving frequency data
echo "Deduplicating events..."
sort "$TEMP_EVENTS" | uniq -c | sort -rn > "$UNIQUE_EVENTS"

# Generate structured timeline report
echo "Generating timeline report..."
cat > "$TIMELINE_FILE" <<EOF
# Crash Timeline Report: $SERVICE

**Incident Period:** $FROM_DATE to $TO_DATE
**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Total Events:** $EVENT_COUNT
**Unique Patterns:** $(wc -l < "$UNIQUE_EVENTS")

## Summary

This report contains the crash timeline extracted from syslog files for the $SERVICE service during the incident period.

## Event Frequency Analysis

Top 20 most frequent events:

\`\`\`
EOF

head -20 "$UNIQUE_EVENTS" >> "$TIMELINE_FILE"

cat >> "$TIMELINE_FILE" <<EOF
\`\`\`

## Daily Breakdown

EOF

# Extract daily counts
echo "Calculating daily event counts..."
awk '{
    # Extract date from RFC 3339 timestamp (first 10 chars of first field)
    timestamp = $1
    if (length(timestamp) >= 10 && substr(timestamp, 5, 1) == "-" && substr(timestamp, 8, 1) == "-") {
        date = substr(timestamp, 1, 10)
        daily[date]++
    }
}
END {
    for (date in daily) {
        print date, daily[date]
    }
}' "$TEMP_EVENTS" | sort >> "$DAILY_COUNTS"

while IFS=' ' read -r date count; do
    echo "- **$date:** $count events" >> "$TIMELINE_FILE"
done < "$DAILY_COUNTS"

cat >> "$TIMELINE_FILE" <<EOF

## Key Events Timeline

### First Occurrence Per Day

EOF

# Extract first occurrence of each failure type per day
awk '{
    # Extract date and time from RFC 3339 timestamp
    timestamp = $1
    if (length(timestamp) >= 19) {
        # Extract date (YYYY-MM-DD)
        date = substr(timestamp, 1, 10)
        # Extract time (HH:MM:SS after the T)
        time = substr(timestamp, 12, 8)

        # Extract failure type/message (simplified - get systemd status)
        if (match($0, /Failed with result/)) {
            type = "service_failed"
        } else if (match($0, /Start request repeated/)) {
            type = "rate_limit"
        } else if (match($0, /crash/)) {
            type = "crash"
        } else if (match($0, /OOM/)) {
            type = "oom"
        } else {
            type = "other"
        }

        key = date "_" type
        if (!seen[key]) {
            seen[key] = 1
            print "**" date " " time "** - " $0
        }
    }
}' "$TEMP_EVENTS" | head -50 >> "$TIMELINE_FILE"

cat >> "$TIMELINE_FILE" <<EOF

## Raw Archive

The complete deduplicated event log has been compressed and stored at:
\`$COMPRESSED_ARCHIVE\`

To extract: \`zstd -d $COMPRESSED_ARCHIVE -c | less\`

## Notes

- Events are deduplicated by unique message content
- Frequency counts show total occurrences across the incident period
- Daily breakdown provides high-level trend analysis
- Raw archive preserves all unique events for forensic analysis
EOF

echo "Timeline report written to: $TIMELINE_FILE"

# Compress raw events
echo "Compressing raw events..."
if command -v zstd &> /dev/null; then
    sort "$TEMP_EVENTS" | uniq > "$RAW_ARCHIVE"
    zstd -19 --rm "$RAW_ARCHIVE" -o "$COMPRESSED_ARCHIVE"
    echo "Compressed archive created: $COMPRESSED_ARCHIVE"
else
    echo "Warning: zstd not found, falling back to gzip"
    sort "$TEMP_EVENTS" | uniq | gzip -9 > "${RAW_ARCHIVE}.gz"
    echo "Compressed archive created: ${RAW_ARCHIVE}.gz"
fi

# Cleanup
rm -f "$TEMP_EVENTS" "$UNIQUE_EVENTS" "$DAILY_COUNTS"

ARCHIVE_SIZE=$(du -sh "$ARCHIVE_DIR" | cut -f1)
echo "Archive complete! Total size: $ARCHIVE_SIZE"
echo ""
echo "Files created:"
echo "  - Timeline report: $TIMELINE_FILE"
echo "  - Compressed archive: $COMPRESSED_ARCHIVE"
