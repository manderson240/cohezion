#!/bin/bash
# COHEZION Repository Optimization Script
# Reduces repository size from 66GB to 10GB target

echo "🚀 Starting COHEZION Repository Optimization..."
echo "📊 Current size: $(du -sh . | cut -f1)"

# Phase 1: Git Cleanup
echo "🧹 Phase 1: Git Cleanup"

# Remove large files from git history (identify first)
echo "📋 Identifying large files in git history..."
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sed -n 's/^blob //p' | sort -nr | head -20 > large_files.txt

# Remove Python cache and temporary files
echo "🗑️  Removing cache files..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name "*.log" -o -name "*.tmp" -o -name "*.cache" -o -name "*.bak" \) -delete 2>/dev/null || true

# Remove build artifacts
echo "🏗️  Removing build artifacts..."
find . -name "*.pyc" -delete
find . -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Phase 2: Git Optimization
echo "📦 Phase 2: Git Optimization"

# Prune unreachable objects
echo "✂️  Pruning unreachable objects..."
git prune --expire=now

# Reflog expiration
echo "📝 Expiring reflog..."
git reflog expire --expire=now --all

# Aggressive garbage collection
echo "🗜️  Running aggressive garbage collection..."
git gc --aggressive --prune=now

# Pack loose objects
echo "📚 Packing loose objects..."
git repack -a -d --depth=250 --window=250

# Phase 3: Large File Management
echo "🐘 Phase 3: Large File Management"

# Create .gitignore for large file patterns
echo "📝 Updating .gitignore..."
cat >> .gitignore << 'EOF'

# Large binary files
*.bin
*.pkl
*.h5
*.hdf5
*.safetensors
*.pth
*.pt

# Dataset files
datasets/
data/
models/

# Cache and temporary files
.cache/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# Build artifacts
build/
dist/
*.egg-info/

# Log files
*.log
logs/

# IDE files
.vscode/
.idea/
*.swp
*.swo
EOF

# Phase 4: Branch Cleanup
echo "🌿 Phase 4: Branch Cleanup"

# Remove stale branches
git remote prune origin
git branch -d $(git branch --merged | grep -v 'main\|master\|develop') 2>/dev/null || true

# Phase 5: Final Optimization
echo "⚡ Phase 5: Final Optimization"

# Clean untracked files
git clean -fdx

# Final garbage collection
git gc --aggressive --prune=now

# Report results
echo "📈 Optimization Complete!"
echo "📊 Final size: $(du -sh . | cut -f1)"
echo "📦 Git objects: $(git count-objects -vH | grep size-pack)"

# Calculate reduction
current_size=$(du -s . | cut -f1)
if [ $current_size -lt 10485760 ]; then  # 10GB in KB
    echo "✅ SUCCESS: Repository size under 10GB target!"
else
    echo "⚠️  Still above 10GB target. Consider:"
    echo "   - Moving large datasets to external storage"
    echo "   - Using Git LFS for binary files"
    echo "   - Removing large model weights"
fi

echo "🎉 COHEZION Repository Optimization Complete!"