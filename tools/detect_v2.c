#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wayland-client.h>
#include "cosmic-toplevel-info-client.h"
#include "ext-foreign-toplevel-list-client.h"

struct toplevel_data {
    int x, y, w, h;
    int has_geometry;
};

struct ext_handle_wrap {
    struct ext_foreign_toplevel_handle_v1 *ext_handle;
    struct zcosmic_toplevel_handle_v1 *cosmic_handle;
    struct toplevel_data data;
};

static struct ext_handle_wrap g_tl[64];
static int g_tl_count = 0;

static struct zcosmic_toplevel_info_v1 *g_info = NULL;
static struct ext_foreign_toplevel_list_v1 *g_ext_list = NULL;
static int g_ext_done = 0;
static int g_info_done = 0;

/* Registry */
static void on_global(void *data, struct wl_registry *registry,
                      uint32_t name, const char *interface, uint32_t version) {
    if (strcmp(interface, zcosmic_toplevel_info_v1_interface.name) == 0 && version >= 3) {
        g_info = wl_registry_bind(registry, name,
            &zcosmic_toplevel_info_v1_interface, 3);
    } else if (strcmp(interface, "ext_foreign_toplevel_list_v1") == 0) {
        g_ext_list = wl_registry_bind(registry, name,
            &ext_foreign_toplevel_list_v1_interface, 1);
    }
}
static void on_global_remove(void *data, struct wl_registry *registry, uint32_t name) {}
static const struct wl_registry_listener reg_listener = { on_global, on_global_remove };

/* Forward declarations */
static const struct zcosmic_toplevel_handle_v1_listener cosmic_handle_listener;

/* zcosmic_toplevel_handle_v1 listener */
static void h_closed(void *d, struct zcosmic_toplevel_handle_v1 *h) {}
static void h_done_ev(void *d, struct zcosmic_toplevel_handle_v1 *h) {
    g_info_done = 1;
}
static void h_title(void *d, struct zcosmic_toplevel_handle_v1 *h, const char *t) {}
static void h_app_id(void *d, struct zcosmic_toplevel_handle_v1 *h, const char *a) {}
static void h_output_enter(void *d, struct zcosmic_toplevel_handle_v1 *h,
                           struct wl_output *o) {}
static void h_output_leave(void *d, struct zcosmic_toplevel_handle_v1 *h,
                           struct wl_output *o) {}
static void h_ws_enter(void *d, struct zcosmic_toplevel_handle_v1 *h,
                       struct zcosmic_workspace_handle_v1 *w) {}
static void h_ws_leave(void *d, struct zcosmic_toplevel_handle_v1 *h,
                       struct zcosmic_workspace_handle_v1 *w) {}
static void h_state(void *d, struct zcosmic_toplevel_handle_v1 *h,
                    struct wl_array *s) {}
static void h_geometry(void *d, struct zcosmic_toplevel_handle_v1 *h,
                       struct wl_output *o, int32_t x, int32_t y,
                       int32_t w, int32_t hh) {
    (void)h; (void)o;
    for (int i = 0; i < g_tl_count; i++) {
        if (g_tl[i].cosmic_handle == h) {
            g_tl[i].data.x = x;
            g_tl[i].data.y = y;
            g_tl[i].data.w = w;
            g_tl[i].data.h = hh;
            g_tl[i].data.has_geometry = 1;
            break;
        }
    }
}
static void h_ext_ws_enter(void *d, struct zcosmic_toplevel_handle_v1 *h,
                           struct ext_workspace_handle_v1 *w) {}
static void h_ext_ws_leave(void *d, struct zcosmic_toplevel_handle_v1 *h,
                           struct ext_workspace_handle_v1 *w) {}

static const struct zcosmic_toplevel_handle_v1_listener cosmic_handle_listener = {
    h_closed, h_done_ev, h_title, h_app_id, h_output_enter, h_output_leave,
    h_ws_enter, h_ws_leave, h_state, h_geometry, h_ext_ws_enter, h_ext_ws_leave,
};

/* ext_foreign_toplevel_handle_v1 listener */
static void ext_closed(void *data, struct ext_foreign_toplevel_handle_v1 *h) {}
static void ext_done_ev(void *data, struct ext_foreign_toplevel_handle_v1 *h) {}
static void ext_title(void *data, struct ext_foreign_toplevel_handle_v1 *h,
                      const char *title) {}
static void ext_app_id(void *data, struct ext_foreign_toplevel_handle_v1 *h,
                       const char *app_id) {}
static void ext_identifier(void *data, struct ext_foreign_toplevel_handle_v1 *h,
                           const char *identifier) {}

static const struct ext_foreign_toplevel_handle_v1_listener ext_handle_listener = {
    ext_closed, ext_done_ev, ext_title, ext_app_id, ext_identifier,
};

/* ext_foreign_toplevel_list_v1 listener */
static void ext_toplevel(void *data, struct ext_foreign_toplevel_list_v1 *list,
                         struct ext_foreign_toplevel_handle_v1 *handle) {
    if (g_tl_count < 64) {
        memset(&g_tl[g_tl_count], 0, sizeof(struct ext_handle_wrap));
        g_tl[g_tl_count].ext_handle = handle;
        g_tl_count++;

        ext_foreign_toplevel_handle_v1_add_listener(handle,
            &ext_handle_listener, NULL);

        if (g_info) {
            struct zcosmic_toplevel_handle_v1 *ch =
                zcosmic_toplevel_info_v1_get_cosmic_toplevel(g_info, handle);
            g_tl[g_tl_count - 1].cosmic_handle = ch;
            zcosmic_toplevel_handle_v1_add_listener(ch,
                &cosmic_handle_listener, NULL);
        }
    }
}
static void ext_list_done(void *data, struct ext_foreign_toplevel_list_v1 *list) {
    g_ext_done = 1;
}

static const struct ext_foreign_toplevel_list_v1_listener ext_list_listener = {
    ext_toplevel, ext_list_done,
};

int main(void) {
    struct wl_display *d = wl_display_connect(NULL);
    if (!d) { printf("[]\n"); return 1; }

    struct wl_registry *r = wl_display_get_registry(d);
    wl_registry_add_listener(r, &reg_listener, NULL);
    wl_display_roundtrip(d);

    if (!g_info || !g_ext_list) {
        wl_display_disconnect(d);
        printf("[]\n");
        return 0;
    }

    ext_foreign_toplevel_list_v1_add_listener(g_ext_list, &ext_list_listener, NULL);

    for (int i = 0; i < 10; i++) {
        wl_display_roundtrip(d);
    }

    printf("[");
    int first = 1;
    for (int i = 0; i < g_tl_count; i++) {
        if (!g_tl[i].data.has_geometry || g_tl[i].data.w < 50 || g_tl[i].data.h < 50)
            continue;
        if (!first) printf(",");
        printf("{\"type\":\"window_top\",\"y\":%d,\"x_start\":%d,\"x_end\":%d,\"height\":%d}",
               g_tl[i].data.y, g_tl[i].data.x,
               g_tl[i].data.x + g_tl[i].data.w, g_tl[i].data.h);
        first = 0;
    }
    printf("]\n");

    wl_display_disconnect(d);
    return 0;
}
