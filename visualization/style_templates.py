"""Modern CSS and styling templates for visualization.

Principles:
- Mobile-first responsive design
- Accessibility (WCAG 2.1 AA compliant)
- Dark mode support
- Professional color scheme
- Fast load times (minimal CSS)
"""


def get_base_css() -> str:
    """Base CSS applied to all pages.
    
    Includes:
    - Reset and normalize
    - CSS variables for theming
    - Responsive grid system
    - Accessibility utilities
    """
    return """
<style>
/* ========================================================================
   RESET & NORMALIZE
   ======================================================================== */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #1a202c;
    background-color: #f7fafc;
}

/* ========================================================================
   CSS CUSTOM PROPERTIES (Theming)
   ======================================================================== */
:root {
    /* Colors - Professional palette */
    --color-primary: #4f46e5;
    --color-primary-dark: #4338ca;
    --color-primary-light: #6366f1;
    
    --color-accent: #7c3aed;
    --color-accent-dark: #6d28d9;
    
    --color-success: #10b981;
    --color-warning: #f59e0b;
    --color-danger: #ef4444;
    --color-info: #3b82f6;
    
    /* Grays */
    --color-gray-50: #f9fafb;
    --color-gray-100: #f3f4f6;
    --color-gray-200: #e5e7eb;
    --color-gray-300: #d1d5db;
    --color-gray-400: #9ca3af;
    --color-gray-500: #6b7280;
    --color-gray-600: #4b5563;
    --color-gray-700: #374151;
    --color-gray-800: #1f2937;
    --color-gray-900: #111827;
    
    /* Spacing */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    --spacing-2xl: 3rem;
    
    /* Border radius */
    --radius-sm: 0.375rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
    --radius-xl: 1rem;
    --radius-full: 9999px;
    
    /* Shadows */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    
    /* Transitions */
    --transition-fast: 150ms ease-in-out;
    --transition-base: 250ms ease-in-out;
    --transition-slow: 350ms ease-in-out;
}

/* Dark mode colors */
@media (prefers-color-scheme: dark) {
    :root {
        --color-text: #f1f5f9;
        --color-bg: #0f172a;
    }
    
    body {
        color: #f1f5f9;
        background-color: #0f172a;
    }
}

/* ========================================================================
   LAYOUT - Container & Grid
   ======================================================================== */
.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: var(--spacing-md);
}

.container-full {
    width: 100%;
}

.grid {
    display: grid;
    gap: var(--spacing-lg);
}

.grid-2 {
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
}

.grid-3 {
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

.grid-4 {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
}

/* ========================================================================
   TYPOGRAPHY
   ======================================================================== */
h1, h2, h3, h4, h5, h6 {
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: var(--spacing-md);
}

h1 {
    font-size: 2.25rem;
}

h2 {
    font-size: 1.875rem;
}

h3 {
    font-size: 1.5rem;
}

h4 {
    font-size: 1.25rem;
}

h5 {
    font-size: 1.125rem;
}

h6 {
    font-size: 1rem;
}

p {
    margin-bottom: var(--spacing-md);
}

.text-muted {
    color: var(--color-gray-500);
}

.text-small {
    font-size: 0.875rem;
}

.text-tiny {
    font-size: 0.75rem;
}

/* ========================================================================
   CARDS
   ======================================================================== */
.card {
    background: white;
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-gray-200);
    box-shadow: var(--shadow-sm);
    transition: box-shadow var(--transition-base), transform var(--transition-base);
}

.card:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
}

.card-header {
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--color-gray-200);
}

.card-body {
    padding: var(--spacing-lg);
}

.card-footer {
    padding: var(--spacing-lg);
    border-top: 1px solid var(--color-gray-200);
}

/* ========================================================================
   BADGES & LABELS
   ======================================================================== */
.badge {
    display: inline-block;
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-full);
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
}

.badge-primary {
    background-color: #e0e7ff;
    color: var(--color-primary-dark);
}

.badge-success {
    background-color: #d1fae5;
    color: #047857;
}

.badge-warning {
    background-color: #fef3c7;
    color: #b45309;
}

.badge-danger {
    background-color: #fee2e2;
    color: #991b1b;
}

/* ========================================================================
   STATS CARDS
   ======================================================================== */
.stat-card {
    background: white;
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    border-left: 4px solid var(--color-primary);
}

.stat-card-label {
    font-size: 0.875rem;
    color: var(--color-gray-500);
    margin-bottom: var(--spacing-sm);
}

.stat-card-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--color-gray-900);
}

.stat-card-unit {
    font-size: 0.875rem;
    color: var(--color-gray-400);
    margin-left: var(--spacing-xs);
}

/* ========================================================================
   BUTTONS
   ======================================================================== */
.btn {
    display: inline-block;
    padding: var(--spacing-sm) var(--spacing-md);
    border: none;
    border-radius: var(--radius-md);
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all var(--transition-fast);
    text-decoration: none;
    user-select: none;
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-primary {
    background-color: var(--color-primary);
    color: white;
}

.btn-primary:hover:not(:disabled) {
    background-color: var(--color-primary-dark);
}

.btn-secondary {
    background-color: var(--color-gray-200);
    color: var(--color-gray-900);
}

.btn-secondary:hover:not(:disabled) {
    background-color: var(--color-gray-300);
}

/* ========================================================================
   TABLES
   ======================================================================== */
.table {
    width: 100%;
    border-collapse: collapse;
}

.table thead {
    background-color: var(--color-gray-50);
    border-bottom: 2px solid var(--color-primary);
}

.table th {
    padding: var(--spacing-md);
    text-align: left;
    font-weight: 700;
    color: var(--color-gray-700);
}

.table td {
    padding: var(--spacing-md);
    border-bottom: 1px solid var(--color-gray-200);
}

.table tbody tr:hover {
    background-color: #f9fafb;
}

.table tbody tr:nth-child(even) {
    background-color: var(--color-gray-50);
}

/* ========================================================================
   SCROLLBARS & OVERFLOW
   ======================================================================== */
.scrollable {
    overflow-y: auto;
    max-height: 600px;
}

/* Webkit scrollbar styling */
.scrollable::-webkit-scrollbar {
    width: 8px;
}

.scrollable::-webkit-scrollbar-track {
    background: var(--color-gray-100);
}

.scrollable::-webkit-scrollbar-thumb {
    background: var(--color-gray-300);
    border-radius: var(--radius-full);
}

.scrollable::-webkit-scrollbar-thumb:hover {
    background: var(--color-gray-400);
}

/* ========================================================================
   UTILITIES
   ======================================================================== */
.flex {
    display: flex;
}

.flex-center {
    display: flex;
    justify-content: center;
    align-items: center;
}

.flex-between {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.gap-sm {
    gap: var(--spacing-sm);
}

.gap-md {
    gap: var(--spacing-md);
}

.gap-lg {
    gap: var(--spacing-lg);
}

.mt-md {
    margin-top: var(--spacing-md);
}

.mb-md {
    margin-bottom: var(--spacing-md);
}

.px-md {
    padding-left: var(--spacing-md);
    padding-right: var(--spacing-md);
}

.py-md {
    padding-top: var(--spacing-md);
    padding-bottom: var(--spacing-md);
}

.rounded {
    border-radius: var(--radius-lg);
}

.shadow-sm {
    box-shadow: var(--shadow-sm);
}

.shadow-md {
    box-shadow: var(--shadow-md);
}

.border {
    border: 1px solid var(--color-gray-200);
}

.bg-white {
    background-color: white;
}

.bg-gray-50 {
    background-color: var(--color-gray-50);
}

.bg-primary {
    background-color: var(--color-primary);
    color: white;
}

/* ========================================================================
   RESPONSIVE
   ======================================================================== */
@media (max-width: 768px) {
    h1 {
        font-size: 1.875rem;
    }
    
    h2 {
        font-size: 1.5rem;
    }
    
    .container {
        padding: var(--spacing-sm);
    }
    
    .grid-2,
    .grid-3,
    .grid-4 {
        grid-template-columns: 1fr;
    }
}

/* ========================================================================
   ACCESSIBILITY
   ======================================================================== */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Focus styles for keyboard navigation */
:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}

/* Skip to main content link */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--color-primary);
    color: white;
    padding: var(--spacing-md);
    text-decoration: none;
    z-index: 100;
}

.skip-link:focus {
    top: 0;
}

</style>
"""


def get_group_css() -> str:
    """CSS specific to equipment group visualization pages.
    
    Includes:
    - Graph container styling
    - Ingredient table styling
    - Ingredient cards
    - Equipment preview gallery
    """
    return """
<style>

/* ========================================================================
   HEADER - Group details
   ======================================================================== */
.group-header {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
    color: white;
    padding: var(--spacing-2xl) var(--spacing-xl);
}

.group-header h1 {
    margin-bottom: var(--spacing-md);
    color: white;
}

.group-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: var(--spacing-lg);
    margin-top: var(--spacing-lg);
}

.group-stat {
    background: rgba(255, 255, 255, 0.1);
    padding: var(--spacing-md);
    border-radius: var(--radius-lg);
    backdrop-filter: blur(10px);
    text-align: center;
}

.group-stat-label {
    font-size: 0.875rem;
    opacity: 0.9;
    margin-bottom: var(--spacing-sm);
}

.group-stat-value {
    font-size: 1.875rem;
    font-weight: 700;
}

/* ========================================================================
   EQUIPMENT PREVIEW GALLERY
   ======================================================================== */
.equipment-gallery {
    padding: var(--spacing-xl);
    background: white;
    border-radius: var(--radius-lg);
    margin-bottom: var(--spacing-lg);
}

.equipment-gallery h3 {
    margin-bottom: var(--spacing-lg);
    color: var(--color-gray-900);
}

.equipment-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: var(--spacing-md);
}

.equipment-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--spacing-md);
    background: var(--color-gray-50);
    border-radius: var(--radius-lg);
    transition: all var(--transition-base);
}

.equipment-item:hover {
    background: white;
    box-shadow: var(--shadow-md);
    transform: translateY(-4px);
}

.equipment-item-image {
    width: 80px;
    height: 80px;
    object-fit: contain;
    margin-bottom: var(--spacing-sm);
}

.equipment-item-fallback {
    width: 80px;
    height: 80px;
    background: linear-gradient(135deg, #e0e7ff, #e0f2fe);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-gray-400);
    font-size: 2rem;
    margin-bottom: var(--spacing-sm);
}

.equipment-item-name {
    font-size: 0.75rem;
    font-weight: 600;
    text-align: center;
    color: var(--color-gray-700);
    line-height: 1.2;
    cursor: pointer;
    transition: all var(--transition-fast);
    border-radius: var(--radius-sm);
    padding: var(--spacing-xs) var(--spacing-sm);
}

.equipment-item-name:hover {
    background-color: var(--color-primary);
    color: white;
    transform: scale(1.05);
}

.equipment-item-name.copied {
    background-color: var(--color-success);
    color: white;
}

.equipment-item-weight {
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--color-primary);
    margin-top: var(--spacing-xs);
    background-color: #f0f4ff;
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
}

/* ========================================================================
   GRAPH CONTAINER
   ======================================================================== */
.graph-container {
    padding: var(--spacing-xl);
    background: white;
    border-radius: var(--radius-lg);
    margin-bottom: var(--spacing-lg);
    min-height: 600px;
    border: 1px solid var(--color-gray-200);
}

.graph-container h3 {
    margin-bottom: var(--spacing-lg);
    color: var(--color-gray-900);
}

#graph {
    width: 100%;
    height: 500px;
}

/* ========================================================================
   INGREDIENT TABLE
   ======================================================================== */
.ingredient-section {
    background: white;
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
}

.ingredient-section h3 {
    margin-bottom: var(--spacing-lg);
    color: var(--color-gray-900);
    border-bottom: 2px solid var(--color-primary);
    padding-bottom: var(--spacing-md);
}

.ingredient-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}

.ingredient-table thead {
    background-color: #f0f4ff;
    border-bottom: 2px solid var(--color-primary);
}

.ingredient-table th {
    padding: var(--spacing-md);
    text-align: left;
    font-weight: 700;
    color: var(--color-primary-dark);
    word-break: break-word;
}

.ingredient-table td {
    padding: var(--spacing-md);
    border-bottom: 1px solid var(--color-gray-200);
    vertical-align: middle;
}

.ingredient-table tbody tr:hover {
    background-color: #f9fafb;
}

/* Resource cell styling */
.ingredient-resource-cell {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.ingredient-resource-icon {
    width: 40px;
    height: 40px;
    object-fit: contain;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: transform var(--transition-base);
}

.ingredient-resource-icon:hover {
    transform: scale(1.2);
}

.ingredient-resource-name {
    font-weight: 600;
    color: var(--color-gray-900);
    cursor: pointer;
    transition: all var(--transition-fast);
    border-radius: var(--radius-sm);
    padding: var(--spacing-xs) var(--spacing-sm);
    display: inline-block;
}

.ingredient-resource-name:hover {
    background-color: var(--color-primary);
    color: white;
    transform: scale(1.02);
}

.ingredient-resource-name.copied {
    background-color: var(--color-success);
    color: white;
}

.ingredient-total {
    text-align: center;
    background-color: #dcfce7;
    font-weight: 700;
    color: #166534;
    border-radius: var(--radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
}

.ingredient-per-equipment {
    text-align: center;
    color: var(--color-gray-600);
}

.ingredient-per-equipment.none {
    color: var(--color-gray-300);
    font-style: italic;
}

/* ========================================================================
   EFFICIENCY INDICATOR
   ======================================================================== */
.efficiency-meter {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.efficiency-bar {
    flex: 1;
    height: 8px;
    background-color: var(--color-gray-200);
    border-radius: var(--radius-full);
    overflow: hidden;
}

.efficiency-fill {
    height: 100%;
    background: linear-gradient(90deg, #10b981, #3b82f6);
    transition: width var(--transition-base);
}

.efficiency-text {
    font-weight: 700;
    font-size: 0.875rem;
    color: var(--color-gray-700);
    min-width: 50px;
}

/* ========================================================================
   COPY TOOLTIP
   ======================================================================== */
.copy-tooltip {
    position: relative;
}

.copy-tooltip-text {
    visibility: hidden;
    background-color: #333;
    color: white;
    text-align: center;
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    position: absolute;
    z-index: 1;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
    opacity: 0;
    transition: opacity var(--transition-fast);
    font-size: 0.75rem;
}

.copy-tooltip:hover .copy-tooltip-text {
    visibility: visible;
    opacity: 1;
}

/* ========================================================================
   RESPONSIVE - Ingredient table
   ======================================================================== */
@media (max-width: 768px) {
    .ingredient-table {
        font-size: 0.8rem;
    }
    
    .ingredient-table th,
    .ingredient-table td {
        padding: var(--spacing-sm);
    }
    
    .equipment-list {
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    }
    
    #graph {
        min-height: 400px;
    }
}

</style>
"""


def get_index_css() -> str:
    """CSS for the index/dashboard page showing all groups.
    
    Includes:
    - Grid layout for group cards
    - Group preview cards
    - Search and filter UI
    """
    return """
<style>

/* ========================================================================
   INDEX HEADER
   ======================================================================== */
.index-header {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
    color: white;
    padding: var(--spacing-2xl) var(--spacing-xl);
    margin-bottom: var(--spacing-2xl);
}

.index-header h1 {
    color: white;
    margin-bottom: var(--spacing-md);
}

.index-header p {
    margin-bottom: var(--spacing-lg);
    opacity: 0.95;
}

.index-controls {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: var(--spacing-md);
    align-items: center;
    margin-top: var(--spacing-lg);
}

.search-box {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: var(--radius-lg);
    padding: var(--spacing-sm) var(--spacing-md);
    color: white;
    font-size: 1rem;
}

.search-box::placeholder {
    color: rgba(255, 255, 255, 0.6);
}

.sort-select {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: var(--radius-lg);
    padding: var(--spacing-sm) var(--spacing-md);
    color: white;
    font-size: 1rem;
    cursor: pointer;
}

.sort-select option {
    background: var(--color-primary);
    color: white;
}

/* ========================================================================
   GROUP CARDS GRID
   ======================================================================== */
.groups-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: var(--spacing-lg);
}

.group-card {
    background: white;
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    transition: all var(--transition-base);
    display: flex;
    flex-direction: column;
}

.group-card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-4px);
}

.group-card-header {
    background: linear-gradient(135deg, #e0e7ff, #f0e7ff);
    padding: var(--spacing-lg);
    border-bottom: 2px solid var(--color-primary);
}

.group-card-title {
    margin: 0;
    font-size: 1.25rem;
    color: var(--color-primary-dark);
}

.group-card-body {
    padding: var(--spacing-lg);
    flex: 1;
}

.group-card-equipment {
    display: block;
    padding: var(--spacing-md) 0;
    margin-bottom: var(--spacing-md);
    border-bottom: 2px solid var(--color-primary-light);
    font-size: 0.9rem;
}

.group-card-equipment-list {
    display: block;
    color: var(--color-gray-700);
    font-weight: 500;
    margin-top: var(--spacing-sm);
    font-size: 0.85rem;
    line-height: 1.4;
}

.group-card-stat {
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--color-gray-100);
    font-size: 0.9rem;
}

.group-card-stat:last-child {
    border-bottom: none;
}

.group-card-stat-label {
    color: var(--color-gray-600);
    font-weight: 600;
}

.group-card-stat-value {
    color: var(--color-gray-900);
    font-weight: 700;
}

.group-card-footer {
    padding: var(--spacing-lg);
    border-top: 1px solid var(--color-gray-200);
    background: var(--color-gray-50);
}

.group-card-link {
    display: inline-block;
    background-color: var(--color-primary);
    color: white;
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    text-decoration: none;
    font-weight: 600;
    transition: background-color var(--transition-fast);
}

.group-card-link:hover {
    background-color: var(--color-primary-dark);
}

/* ========================================================================
   INDEX SUMMARY
   ======================================================================== */
.index-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-2xl);
}

.summary-card {
    background: white;
    padding: var(--spacing-xl);
    border-radius: var(--radius-lg);
    border-left: 4px solid var(--color-primary);
    box-shadow: var(--shadow-sm);
}

.summary-label {
    font-size: 0.875rem;
    color: var(--color-gray-600);
    margin-bottom: var(--spacing-sm);
}

.summary-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--color-gray-900);
}

/* ========================================================================
   NO RESULTS
   ======================================================================== */
.no-results {
    text-align: center;
    padding: var(--spacing-2xl);
    color: var(--color-gray-500);
}

.no-results-icon {
    font-size: 3rem;
    margin-bottom: var(--spacing-lg);
}

/* ========================================================================
   RESPONSIVE
   ======================================================================== */
@media (max-width: 768px) {
    .index-controls {
        grid-template-columns: 1fr;
    }
    
    .groups-container {
        grid-template-columns: 1fr;
    }
}

</style>
"""


def get_javascript_utils() -> str:
    """Utility JavaScript functions for interactivity.
    
    Features:
    - Copy to clipboard with feedback
    - Resource search/filter
    - Tooltip management
    - Modal dialogs
    """
    return """
<script>
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
        // Re-fetch the text from data attribute if available, otherwise restore original
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
</script>
"""
