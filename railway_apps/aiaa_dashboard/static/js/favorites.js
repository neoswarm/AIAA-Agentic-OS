/**
 * Favorites System - Star toggle on workflow cards
 */

async function toggleFavorite(workflowName) {
    const button = document.querySelector(`button[onclick*="${workflowName}"]`);
    const isFavorite = button.getAttribute('data-favorite') === 'true';
    
    try {
        const response = await fetch('/api/favorites/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                workflow_name: workflowName
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            const newState = result.favorite;
            
            // Update button state
            button.setAttribute('data-favorite', newState);
            button.title = newState ? 'Remove from favorites' : 'Add to favorites';
            
            // Update star icon
            const svg = button.querySelector('svg');
            if (svg) {
                svg.setAttribute('fill', newState ? 'var(--accent)' : 'none');
            }
            
            // Optional: Reload page to update favorites section
            if (window.location.pathname === '/workflows') {
                setTimeout(() => {
                    window.location.reload();
                }, 300);
            }
        } else {
            console.error('Failed to toggle favorite');
        }
    } catch (error) {
        console.error('Error toggling favorite:', error);
    }
}

// Load favorites on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/favorites');
        if (response.ok) {
            const favorites = await response.json();
            
            // Update all favorite buttons
            favorites.forEach(workflowName => {
                const button = document.querySelector(`button[onclick*="${workflowName}"]`);
                if (button) {
                    button.setAttribute('data-favorite', 'true');
                    const svg = button.querySelector('svg');
                    if (svg) {
                        svg.setAttribute('fill', 'var(--accent)');
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading favorites:', error);
    }
});
