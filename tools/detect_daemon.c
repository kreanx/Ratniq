#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <poll.h>
#include <signal.h>
#include <wayland-client.h>
#include "cosmic-toplevel-info-client.h"
#include "ext-foreign-toplevel-list-client.h"

struct tl_data {
    int x, y, w, h;
    int has_geo;
    int alive;
    char app_id[128];
};

static struct tl_data g_data[64];
static struct zcosmic_toplevel_handle_v1 *g_ch[64];
static struct ext_foreign_toplevel_handle_v1 *g_eh[64];
static int g_count = 0;
static volatile int g_dirty = 1;
static volatile int g_running = 1;

static struct zcosmic_toplevel_info_v1 *g_info = NULL;
static struct ext_foreign_toplevel_list_v1 *g_ext = NULL;
static struct wl_display *g_display = NULL;

static void sig_handler(int sig) { g_running = 0; }

static void emit_json(void) {
    printf("[");
    int first = 1;
    for (int i = 0; i < g_count; i++) {
        if (!g_data[i].alive || !g_data[i].has_geo) continue;
        if (g_data[i].w < 50 || g_data[i].h < 50) continue;
        if (!first) printf(",");
        printf("{\"type\":\"window_top\",\"y\":%d,\"x_start\":%d,\"x_end\":%d,\"height\":%d,\"app_id\":\"%s\"}",
               g_data[i].y, g_data[i].x, g_data[i].x + g_data[i].w,
               g_data[i].h, g_data[i].app_id);
        first = 0;
    }
    printf("]\n");
    fflush(stdout);
}

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

static void h_closed(void *d, struct zcosmic_toplevel_handle_v1 *h) {
    for (int i = 0; i < g_count; i++) {
        if (g_ch[i] == h) { g_data[i].alive = 0; g_dirty = 1; break; }
    }
}
static void h_done(void *d, struct zcosmic_toplevel_handle_v1 *h) {}
static void h_title(void *d, struct zcosmic_toplevel_handle_v1 *h, const char *t) {}

static void h_app_id(void *d, struct zcosmic_toplevel_handle_v1 *h, const char *a) {
    for (int i = 0; i < g_count; i++) {
        if (g_ch[i] == h) {
            strncpy(g_data[i].app_id, a ? a : "", 127);
            g_data[i].app_id[127] = '\0';
            g_dirty = 1;
            break;
        }
    }
}

static void h_oe(void *d, struct zcosmic_toplevel_handle_v1 *h, struct wl_output *o) {}
static void h_ol(void *d, struct zcosmic_toplevel_handle_v1 *h, struct wl_output *o) {}
static void h_ws_e(void *d, struct zcosmic_toplevel_handle_v1 *h, struct zcosmic_workspace_handle_v1 *w) {}
static void h_ws_l(void *d, struct zcosmic_toplevel_handle_v1 *h, struct zcosmic_workspace_handle_v1 *w) {}
static void h_state(void *d, struct zcosmic_toplevel_handle_v1 *h, struct wl_array *s) {
    for (int i = 0; i < g_count; i++) {
        if (g_ch[i] == h) { g_dirty = 1; break; }
    }
}

static void h_geo(void *d, struct zcosmic_toplevel_handle_v1 *h,
                  struct wl_output *o, int32_t x, int32_t y, int32_t w, int32_t hh) {
    for (int i = 0; i < g_count; i++) {
        if (g_ch[i] == h) {
            if (g_data[i].x != x || g_data[i].y != y ||
                g_data[i].w != w || g_data[i].h != hh) {
                g_dirty = 1;
            }
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
static void ext_app_id(void *d, struct ext_foreign_toplevel_handle_v1 *h, const char *a) {
    for (int i = 0; i < g_count; i++) {
        if (g_eh[i] == h) {
            strncpy(g_data[i].app_id, a ? a : "", 127);
            g_data[i].app_id[127] = '\0';
            g_dirty = 1;
            break;
        }
    }
}
static void ext_id(void *d, struct ext_foreign_toplevel_handle_v1 *h, const char *id) {}
static const struct ext_foreign_toplevel_handle_v1_listener ehl = {
    ext_closed, ext_done, ext_title, ext_app_id, ext_id,
};

static void ext_tl(void *d, struct ext_foreign_toplevel_list_v1 *list,
                   struct ext_foreign_toplevel_handle_v1 *handle) {
    if (g_count >= 64) return;
    ext_foreign_toplevel_handle_v1_add_listener(handle, &ehl, NULL);
    g_eh[g_count] = handle;
    if (g_info) {
        struct zcosmic_toplevel_handle_v1 *ch =
            zcosmic_toplevel_info_v1_get_cosmic_toplevel(g_info, handle);
        g_ch[g_count] = ch;
        memset(&g_data[g_count], 0, sizeof(struct tl_data));
        g_data[g_count].alive = 1;
        g_count++;
        g_dirty = 1;
        zcosmic_toplevel_handle_v1_add_listener(ch, &hl, NULL);
    }
}
static void ext_list_done(void *d, struct ext_foreign_toplevel_list_v1 *list) {}
static const struct ext_foreign_toplevel_list_v1_listener ell = { ext_tl, ext_list_done };

int main(void) {
    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    g_display = wl_display_connect(NULL);
    if (!g_display) { fprintf(stderr, "[]\n"); return 1; }

    struct wl_registry *r = wl_display_get_registry(g_display);
    wl_registry_add_listener(r, &rl, NULL);
    wl_display_roundtrip(g_display);

    if (!g_info || !g_ext) {
        wl_display_disconnect(g_display);
        fprintf(stderr, "[]\n");
        return 0;
    }

    ext_foreign_toplevel_list_v1_add_listener(g_ext, &ell, NULL);
    wl_display_roundtrip(g_display);

    for (int i = 0; i < 50 && g_running; i++) {
        wl_display_dispatch_pending(g_display);
        wl_display_flush(g_display);
        struct pollfd pfd = { wl_display_get_fd(g_display), POLLIN, 0 };
        poll(&pfd, 1, 50);
        if (pfd.revents & POLLIN) wl_display_dispatch(g_display);
    }

    if (g_dirty) { emit_json(); g_dirty = 0; }

    while (g_running) {
        wl_display_dispatch_pending(g_display);
        if (wl_display_flush(g_display) < 0) break;

        struct pollfd pfd = { wl_display_get_fd(g_display), POLLIN, 0 };
        int ret = poll(&pfd, 1, -1);
        if (ret < 0) break;
        if (pfd.revents & POLLIN) {
            if (wl_display_dispatch(g_display) < 0) break;
        }

        if (g_dirty) { emit_json(); g_dirty = 0; }
    }

    wl_display_disconnect(g_display);
    return 0;
}
