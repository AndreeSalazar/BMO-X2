// Ring 3 diagnostic view. Neither opening nor closing it calls Ring 0.
static Rml::String rtx_lab_report(unsigned amdvi_status, bool translation,
                                 unsigned firmware_status, unsigned prep_status) {
    const char* iommu = amdvi_status != 4 ? "SIN CAPTURA" :
                        translation ? "ACTIVA EN LA CAPTURA" : "DESACTIVADA";
    const char* firmware = firmware_status == 5 && prep_status == 7 ? "FWSEC PREPARADO" :
                           firmware_status == 5 ? "CONTENEDOR CARGADO" : "SIN EVIDENCIA";
    Rml::String html = "<h2>RTX / Prueba de arranque</h2><p>F4 cerrar</p>";
    html += "<p>Traduccion AMD-Vi: ";
    html += iommu;
    html += "</p><p>Preparacion NVIDIA: ";
    html += firmware;
    html += "</p><p>USB con DMA traducido: PENDIENTE</p>"
            "<p>DMA limitado de la RTX: PENDIENTE</p>"
            "<p>Respuesta del GSP: PENDIENTE</p>"
            "<p>Primer triangulo: PENDIENTE</p>";
    return html;
}
