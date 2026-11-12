/*!
 * Start Bootstrap - SB Admin Pro v2.0.5
 * Custom Talena sidebar handling
 */

window.addEventListener("DOMContentLoaded", () => {
    /* --------------------------------
       Feather icons
    -------------------------------- */
    if (typeof feather !== "undefined") {
        feather.replace();
    }

    /* --------------------------------
       Bootstrap tooltips
    -------------------------------- */
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );

    tooltipTriggerList.map((tooltipTriggerEl) => {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    /* --------------------------------
       Bootstrap popovers
    -------------------------------- */
    const popoverTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="popover"]')
    );

    popoverTriggerList.map((popoverTriggerEl) => {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    /* --------------------------------
       Sidebar toggle
    -------------------------------- */

    const sidebarToggle = document.querySelector("#sidebarToggle");
    const sidebarToggleDesktop = document.querySelector("#sidebarToggleDesktop");

    function toggleSidebar(event) {
        if (event) {
            event.preventDefault();
        }

        document.body.classList.toggle("sidenav-toggled");

        localStorage.setItem(
            "sb|sidebar-toggle",
            document.body.classList.contains("sidenav-toggled")
        );
    }

    /*
     * Restore sidebar state on page load.
     * If you do NOT want it to remember closed/open state between pages,
     * remove this block.
     */
    if (localStorage.getItem("sb|sidebar-toggle") === "true") {
        document.body.classList.add("sidenav-toggled");
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", toggleSidebar);
    }

    if (sidebarToggleDesktop) {
        sidebarToggleDesktop.addEventListener("click", toggleSidebar);
    }

    /* --------------------------------
       Close sidebar on mobile when clicking content
    -------------------------------- */

    const sidenavContent = document.querySelector("#layoutSidenav_content");

    if (sidenavContent) {
        sidenavContent.addEventListener("click", () => {
            const BOOTSTRAP_LG_WIDTH = 992;

            if (window.innerWidth >= BOOTSTRAP_LG_WIDTH) {
                return;
            }

            if (document.body.classList.contains("sidenav-toggled")) {
                document.body.classList.remove("sidenav-toggled");
                localStorage.setItem("sb|sidebar-toggle", "false");
            }
        });
    }

    /* --------------------------------
       Active state for sidebar nav links
       This is mostly SB Admin fallback.
       Your Django active classes can still handle this better.
    -------------------------------- */

    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll(".sidenav .nav-link");

    navLinks.forEach((link) => {
        const href = link.getAttribute("href");

        if (!href) {
            return;
        }

        try {
            const linkUrl = new URL(href, window.location.origin);

            if (linkUrl.pathname === currentPath) {
                link.classList.add("active");

                let parentNode = link.parentNode;

                while (parentNode && parentNode !== document.documentElement) {
                    if (parentNode.classList.contains("collapse")) {
                        parentNode.classList.add("show");

                        const parentNavLink = document.querySelector(
                            `[data-bs-target="#${parentNode.id}"]`
                        );

                        if (parentNavLink) {
                            parentNavLink.classList.remove("collapsed");
                            parentNavLink.classList.add("active");
                        }
                    }

                    parentNode = parentNode.parentNode;
                }
            }
        } catch (error) {
            // Ignore invalid hrefs like javascript:void(0)
        }
    });
});