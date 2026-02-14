# COHEZION Repository Optimization Guide

## 🎯 Objective: Reduce repository size from 66GB to 10GB

### 📊 Current Status Analysis
- **Repository Size**: 66GB → Need to reduce to 10GB (84.8% reduction)
- **Git Objects**: 4.4M objects, 7.02GB in pack files
- **Primary Issue**: Large binary assets and git history bloat

### 🚀 Immediate Actions (High Impact)

#### 1. Git History Optimization
```bash
# Remove large files from git history
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch large-files/*' --prune-empty --tag-name-filter cat -- --all

# Compress remaining history
git gc --aggressive --prune=now
```

#### 2. Large File Management
- Move datasets to external storage
- Use Git LFS for large binary files
- Implement .gitignore for generated assets

#### 3. Branch Cleanup
```bash
# Remove stale branches
git remote prune origin
git branch -d $(git branch --merged | grep -v 'main\|master\|develop')
```

### 📁 File Structure Optimization

#### Remove/Externalize:
- Large model weights (>100MB)
- Dataset files (>50MB)
- Build artifacts
- Temporary simulation results
- Log files and caches

#### Keep in Repository:
- Core Python modules
- Configuration files
- Documentation
- Small test datasets
- Setup scripts

### 🔧 Technical Implementation

#### Git LFS Setup
```bash
# Install Git LFS
git lfs install

# Track large files
git lfs track "*.bin"
git lfs track "*.pkl"
git lfs track "*.h5"
git lfs track "*.safetensors"
```

#### Clean Commands
```bash
# Remove untracked files
git clean -fdx

# Reset to clean state
git reset --hard HEAD

# Full repository cleanup
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
```

### 📈 Progress Tracking
- [ ] Git history cleanup
- [ ] Large file externalization
- [ ] Cache/temporary file removal
- [ ] Branch cleanup
- [ ] LFS implementation
- [ ] Final compression

### 🎯 Expected Results
- Git objects: 7.02GB → ~2GB
- Binary assets: External storage
- Cache files: Removed
- Total size: 66GB → 10-15GB

### ⚡ Automation Scripts
Create automated cleanup pipeline for maintenance:
- Weekly git garbage collection
- Monthly large file audit
- Automated cache cleanup