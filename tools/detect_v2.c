#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <poll.h>
#include <wayland-client.h>
#include "cosmic-toplevel-info-client.h"
#include "ext-foreign-toplevel-list-client.h"

struct tl_data { int x,y,w,h; int has_geo; };
static struct tl_data g_data[64];
static struct zcosmic_toplevel_handle_v1 *g_ch[64];
static int g_count = 0;
static struct zcosmic_toplevel_info_v1 *g_info = NULL;
static struct ext_foreign_toplevel_list_v1 *g_ext = NULL;

static void on_global(void *data, struct wl_registry *r, uint32_t name,
                      const char *iface, uint32_t ver) {
    if (strcmp(iface, zcosmic_toplevel_info_v1_interface.name) == 0 && ver >= 2)
        g_info = wl_registry_bind(r, name, &zcosmic_toplevel_info_v1_interface, 2);
    else if (strcmp(iface, ext_foreign_toplevel_list_v1_interface.name) == 0)
        g_ext = wl_registry_bind(r, name, &ext_foreign_toplevel_list_v1_interface, 1);
    else if (strcmp(iface, "wl_output") == 0)
        wl_registry_bind(r, name, &wl_output_interface, 1);
}
static void on_global_remove(void *data, struct wl_registry *r, uint32_t name) {}
static const struct wl_registry_listener rl = { on_global, on_global_remove };

static void h_closed(void *d, struct zcosmic_toplevel_handle_v1 *h) {}
static void h_done(void *d, struct zcosmic_toplevel_handle_v1 *h) {}
static void h_title(void *d, struct zcosmic_toplevel_handle_v1 *h, const char *t) {}
static void h_app_id(void *d, struct zcosmic_toplevel_handle_v1 *h, const char *a) {}
static void h_oe(void *d, struct zcosmic_toplevel_handle_v1 *h, struct wl_output *o) {}
static void h_ol(void *d, struct zcosmic_toplevel_handle_v1 *h, struct wl_output *o) {}
static void h_ws_e(void *d, struct zcosmic_toplevel_handle_v1 *h, struct zcosmic_workspace_handle_v1 *w) {}
static void h_ws_l(void *d, struct zcosmic_toplevel_handle_v1 *h, struct zcosmic_workspace_handle_v1 *w) {}
static void h_state(void *d, struct zcosmic_toplevel_handle_v1 *h, struct wl_array *s) {}
static void h_geo(void *d, struct zcosmic_toplevel_handle_v1 *h,
                  struct wl_output *o, int32_t x, int32_t y, int32_t w, int32_t hh) {
    for (int i = 0; i < g_count; i++) {
        if (g_ch[i] == h) {
            g_data[i].x = x;
            g_data[i].y = y;
            g_data[i].w = w;
            g_data[i].h = hh;
            g_data[i].has_geo = 1;
            break;
        }
    }
}
static void h_ews_e(void *d, struct zcosmic_toplevel_handle_v1 *h, struct ext_workspace_handle_v1 *w) {}
static void h_ews_l(void *d, struct zcosmic_toplevel_handle_v1 *h, struct ext_workspace_handle_v1 *w) {}
static const struct zcosmic_toplevel_handle_v1_listener hl = {
    h_closed, h_done, h_title, h_app_id, h_oe, h_ol,
    h_ws_e, h_ws_l, h_state, h_geo, h_ews_e, h_ews_l,
};

static void ext_closed(void *d, struct ext_foreign_toplevel_handle_v1 *h) {}
static void ext_done(void *d, struct ext_foreign_toplevel_handle_v1 *h) {}
static void ext_title(void *d, struct ext_foreign_toplevel_handle_v1 *h, const char *t) {}
static void ext_app_id(void *d, struct ext_foreign_toplevel_handle_v1 *h, const char *a) {}
static void ext_id(void *d, struct ext_foreign_toplevel_handle_v1 *h, const char *id) {}
static const struct ext_foreign_toplevel_handle_v1_listener ehl = {
    ext_closed, ext_done, ext_title, ext_app_id, ext_id,
};

static void ext_tl(void *d, struct ext_foreign_toplevel_list_v1 *list,
                   struct ext_foreign_toplevel_handle_v1 *handle) {
    if (g_count >= 64) return;
    ext_foreign_toplevel_handle_v1_add_listener(handle, &ehl, NULL);
    if (g_info) {
        struct zcosmic_toplevel_handle_v1 *ch =
            zcosmic_toplevel_info_v1_get_cosmic_toplevel(g_info, handle);
        g_ch[g_count] = ch;
        memset(&g_data[g_count], 0, sizeof(struct tl_data));
        g_count++;
        zcosmic_toplevel_handle_v1_add_listener(ch, &hl, NULL);
    }
}
static void ext_list_done(void *d, struct ext_foreign_toplevel_list_v1 *list) {}
static const struct ext_foreign_toplevel_list_v1_listener ell = { ext_tl, ext_list_done };

static int read_ev(struct wl_display *d) {
    wl_display_dispatch_pending(d);
    if (wl_display_flush(d) < 0) return -1;
    struct pollfd pfd = { wl_display_get_fd(d), POLLIN, 0 };
    if (poll(&pfd, 1, 100) < 0) return -1;
    if (pfd.revents & POLLIN) {
        if (wl_display_dispatch(d) < 0) return -1;
    }
    return 0;
}

int main(void) {
    struct wl_display *d = wl_display_connect(NULL);
    if (!d) { printf("[]\n"); return 1; }
    struct wl_registry *r = wl_display_get_registry(d);
    wl_registry_add_listener(r, &rl, NULL);
    wl_display_roundtrip(d);

    if (!g_info || !g_ext) { wl_display_disconnect(d); printf("[]\n"); return 0; }

    ext_foreign_toplevel_list_v1_add_listener(g_ext, &ell, NULL);
    wl_display_roundtrip(d);

    for (int i = 0; i < 30; i++) {
        if (read_ev(d) < 0) break;
    }

    printf("[");
    int first = 1;
    for (int i = 0; i < g_count; i++) {
        if (!g_data[i].has_geo || g_data[i].w < 50 || g_data[i].h < 50) continue;
        if (!first) printf(",");
        printf("{\"type\":\"window_top\",\"y\":%d,\"x_start\":%d,\"x_end\":%d,\"height\":%d}",
               g_data[i].y, g_data[i].x, g_data[i].x + g_data[i].w, g_data[i].h);
        first = 0;
    }
    printf("]\n");

    wl_display_disconnect(d);
    return 0;
}
