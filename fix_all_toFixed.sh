#!/bin/bash
# Comprehensive toFixed fix across all worktrees and main repo

echo "🔧 Fixing ALL toFixed errors across worktrees..."

cd /home/mike-anderson/dev/cohezion

# Function to fix files in a directory
fix_in_dir() {
    local dir=$1
    
    # apps/webapp/src/components/LandingPage.tsx
    if [ -f "$dir/apps/webapp/src/components/LandingPage.tsx" ]; then
        sed -i 's/ouroboros\.coherence\.toFixed/(ouroboros.coherence ?? 0).toFixed/g' "$dir/apps/webapp/src/components/LandingPage.tsx"
        sed -i 's/ouroboros\.entropy\.toFixed/(ouroboros.entropy ?? 0).toFixed/g' "$dir/apps/webapp/src/components/LandingPage.tsx"
        echo "  ✓ Fixed LandingPage.tsx in $dir"
    fi
    
    # apps/webapp/src/components/Universe/ManifoldCanvas.tsx
    if [ -f "$dir/apps/webapp/src/components/Universe/ManifoldCanvas.tsx" ]; then
        sed -i 's/latestPoint\.coherence\.toFixed/latestPoint.coherence?.toFixed/g' "$dir/apps/webapp/src/components/Universe/ManifoldCanvas.tsx"
        sed -i 's/v => v\.toFixed/v => (v ?? 0).toFixed/g' "$dir/apps/webapp/src/components/Universe/ManifoldCanvas.tsx"
        echo "  ✓ Fixed ManifoldCanvas.tsx in $dir"
    fi
    
    # apps/webapp/src/components/Universe/HologramField.tsx
    if [ -f "$dir/apps/webapp/src/components/Universe/HologramField.tsx" ]; then
        sed -i 's/randomNode\.coherence?\.toFixed/(randomNode.coherence ?? 0).toFixed/g' "$dir/apps/webapp/src/components/Universe/HologramField.tsx"
        echo "  ✓ Fixed HologramField.tsx in $dir"
    fi
    
    # apps/morphospace-loom/src/App.tsx
    if [ -f "$dir/apps/morphospace-loom/src/App.tsx" ]; then
        sed -i 's/{value\.toFixed/(value ?? 0).toFixed/g' "$dir/apps/morphospace-loom/src/App.tsx"
        sed -i 's/{d1\.toFixed/(d1 ?? 0).toFixed/g' "$dir/apps/morphospace-loom/src/App.tsx"
        sed -i 's/{d12\.toFixed/(d12 ?? 0).toFixed/g' "$dir/apps/morphospace-loom/src/App.tsx"
        echo "  ✓ Fixed morphospace-loom/App.tsx in $dir"
    fi
    
    # src/web/anima_dashboard/src/components/OuroborosControlRoom.tsx
    if [ -f "$dir/src/web/anima_dashboard/src/components/OuroborosControlRoom.tsx" ]; then
        sed -i 's/evo\.charge_density\.toFixed/(evo.charge_density ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/OuroborosControlRoom.tsx"
        sed -i 's/evo\.magnetic_helicity\.toFixed/(evo.magnetic_helicity ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/OuroborosControlRoom.tsx"
        sed -i 's/evo\.toroidal_moment\.toFixed/(evo.toroidal_moment ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/OuroborosControlRoom.tsx"
        sed -i 's/evo\.coherence\.toFixed/(evo.coherence ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/OuroborosControlRoom.tsx"
        echo "  ✓ Fixed OuroborosControlRoom.tsx in $dir"
    fi
    
    # src/web/anima_dashboard/src/components/FreezeFrame.tsx
    if [ -f "$dir/src/web/anima_dashboard/src/components/FreezeFrame.tsx" ]; then
        sed -i 's/state\.coherence\.toFixed/(state.coherence ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/FreezeFrame.tsx"
        echo "  ✓ Fixed FreezeFrame.tsx in $dir"
    fi
    
    # src/web/anima_dashboard/src/components/JourneyStatus.tsx
    if [ -f "$dir/src/web/anima_dashboard/src/components/JourneyStatus.tsx" ]; then
        sed -i 's/displayData\.coherence\.toFixed/(displayData.coherence ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/JourneyStatus.tsx"
        echo "  ✓ Fixed JourneyStatus.tsx in $dir"
    fi
    
    # src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx
    if [ -f "$dir/src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx" ]; then
        sed -i 's/value: coherence\.toFixed/value: (coherence ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx"
        sed -i 's/evo\.charge_density\.toFixed/(evo.charge_density ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx"
        echo "  ✓ Fixed ObservatoryMode.tsx in $dir"
    fi
    
    # src/web/anima_dashboard/src/components/AnimaNarrationBar.tsx
    if [ -f "$dir/src/web/anima_dashboard/src/components/AnimaNarrationBar.tsx" ]; then
        sed -i 's/coherence\.toFixed/(coherence ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/AnimaNarrationBar.tsx"
        echo "  ✓ Fixed AnimaNarrationBar.tsx in $dir"
    fi
    
    # src/web/anima_dashboard/src/components/PersistenceDiagram.tsx
    if [ -f "$dir/src/web/anima_dashboard/src/components/PersistenceDiagram.tsx" ]; then
        sed -i 's/topology\.entropy\.toFixed/(topology.entropy ?? 0).toFixed/g' "$dir/src/web/anima_dashboard/src/components/PersistenceDiagram.tsx"
        echo "  ✓ Fixed PersistenceDiagram.tsx in $dir"
    fi
}

# Fix main repo
echo "📁 Fixing main repo..."
fix_in_dir "."

# Fix all worktrees
for worktree in .worktrees/*/; do
    if [ -d "$worktree" ]; then
        echo "📁 Fixing $worktree..."
        fix_in_dir "$worktree"
    fi
done

echo ""
echo "✅ All toFixed errors fixed across all worktrees!"
echo ""
echo "Run 'git status' to see changed files, then commit."
