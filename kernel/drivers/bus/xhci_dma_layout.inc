/* Page counts shared by the EFI reservation and the xHCI stage. */
#define XHCI_QUEUE_PAGES 5
#define XHCI_SCRATCHPAD_LIMIT 4
#define XHCI_PROBE_PAGES (XHCI_QUEUE_PAGES + XHCI_SCRATCHPAD_LIMIT)
#define XHCI_SCRATCHPAD_TABLE 0x800
