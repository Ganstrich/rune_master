/**
 * Utility: Copy text to clipboard with user feedback
 * Shows temporary tooltip indicating successful copy
 */
function copyToClipboard(text, element) {
    if (!navigator.clipboard) {
        // Fallback for older browsers
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    } else {
        navigator.clipboard.writeText(text);
    }
    
    // Show feedback
    const originalClass = element.className;
    element.classList.add('copied');
    element.textContent = '✓ Copied!';
    
    setTimeout(() => {
        element.className = originalClass;
        const originalText = element.getAttribute('data-original-text');
        if (originalText) {
            element.textContent = originalText;
        }
    }, 1500);
}

/**
 * Copy equipment or resource name and show tooltip
 */
function copyName(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const element = event.target;
    const textToCopy = element.getAttribute('data-copy-text') || element.textContent;
    
    // Store original text for restoration
    if (!element.getAttribute('data-original-text')) {
        element.setAttribute('data-original-text', element.textContent);
    }
    
    copyToClipboard(textToCopy, element);
}

/**
 * Copy resource name and show tooltip
 */
function copyResourceName(resourceName) {
    copyToClipboard(resourceName, event.target);
}

/**
 * Search/filter functionality for ingredient table
 */
function filterIngredients(searchTerm) {
    const table = document.querySelector('.ingredient-table tbody');
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const resourceName = row.querySelector('.ingredient-resource-name')?.textContent.toLowerCase() || '';
        const isVisible = resourceName.includes(term) || term === '';
        row.style.display = isVisible ? '' : 'none';
    });
}

/**
 * Sort ingredients table by column
 */
function sortIngredientsBy(columnIndex, order = 'asc') {
    const table = document.querySelector('.ingredient-table tbody');
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aVal = a.querySelectorAll('td')[columnIndex]?.textContent.trim() || '';
        const bVal = b.querySelectorAll('td')[columnIndex]?.textContent.trim() || '';
        
        // Try numeric sort if both are numbers
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return order === 'asc' ? aNum - bNum : bNum - aNum;
        }
        
        // Fallback to string sort
        return order === 'asc' 
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
    });
    
    // Re-append sorted rows
    rows.forEach(row => table.appendChild(row));
}

/**
 * D3.js graph initialization (called by graph-specific pages)
 * This is a placeholder - actual D3 setup is in graph_generator.py
 */
function initializeGraph(graphData) {
    console.log('Graph data loaded:', graphData);
    // D3 setup code will go here
}

/**
 * Smooth scroll to element
 */
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

/**
 * Toggle element visibility with smooth animation
 */
function toggleElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = element.style.display === 'none' ? '' : 'none';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add click listeners to equipment names
    document.querySelectorAll('.equipment-item-name').forEach(element => {
        element.addEventListener('click', copyName);
    });
    
    // Add click listeners to resource names
    document.querySelectorAll('.ingredient-resource-name').forEach(element => {
        element.addEventListener('click', copyName);
    });
    
    // Add event listeners to copy buttons
    document.querySelectorAll('.copy-tooltip').forEach(element => {
        element.addEventListener('click', function(e) {
            const text = e.target.getAttribute('data-copy-text') || e.target.textContent;
            copyToClipboard(text, e.target);
        });
    });
    
    // Add search box listener if it exists
    const searchBox = document.getElementById('ingredient-search');
    if (searchBox) {
        searchBox.addEventListener('input', function(e) {
            filterIngredients(e.target.value);
        });
    }
});
