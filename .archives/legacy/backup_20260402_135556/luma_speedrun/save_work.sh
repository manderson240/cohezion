#!/bin/bash
# Save all AMD speedrun work before reboot

echo "=== Saving AMD Speedrun Work ==="
echo "Timestamp: $(date)"
echo ""

# Create backup directory
BACKUP_DIR="/home/mike-anderson/dev/cohezion/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "1. Backing up luma_speedrun directory..."
cp -r /home/mike-anderson/dev/cohezion/luma_speedrun "$BACKUP_DIR/"

echo "2. Creating submission inventory..."
cd /home/mike-anderson/dev/cohezion/luma_speedrun

for dir in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
    echo "  - $dir: $(ls -1 $dir/submission*.py 2>/dev/null | wc -l) submission files"
done

echo "3. Backing up autoresearch..."
if [ -d "autoresearch" ]; then
    cp -r autoresearch "$BACKUP_DIR/"
fi

echo "4. Creating archive manifest..."
cat > "$BACKUP_DIR/MANIFEST.txt" << EOF
AMD Speedrun Backup
===================
Created: $(date)
Source: /home/mike-anderson/dev/cohezion/luma_speedrun/

Contents:
- amd-mixed-mla/ : MLA decode variants
- amd-moe-mxfp4/ : MoE variants  
- amd-mxfp4-mm/ : GEMM variants
- autoresearch/ : K-Search infrastructure
- ARCHIVE.md : Session summary
- *.sh : Submission scripts

Submission IDs:
- MLA Latest: 677959
- MoE Latest: 677786
- GEMM Latest: 677637

Status: All submissions complete (done)
EOF

echo "5. Compressing backup..."
cd /home/mike-anderson/dev/cohezion
tar -czf "amd_speedrun_backup_$(date +%Y%m%d_%H%M%S).tar.gz" "$(basename $BACKUP_DIR)"

echo ""
echo "=== Backup Complete ==="
echo "Location: $BACKUP_DIR"
echo "Archive: /home/mike-anderson/dev/cohezion/amd_speedrun_backup_*.tar.gz"
echo "Total files: $(find $BACKUP_DIR -type f | wc -l)"
