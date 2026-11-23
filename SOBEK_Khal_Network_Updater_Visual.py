from collections import Counter
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import geopandas as gpd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, snap, unary_union

HEADER_LINE = (
    '"NTW6.6","\\SOBEK216\\Pay_hyd.lit\\CMTWORK\\ntrpluv.ini","SOBEK-LITE-3B,'
    ' edit network"\n'
)
REPO_URL = "https://github.com/arafatkabirrony/sobek-khal-network-updater"


class SOBEKKhalUpdaterVisualApp:

  def __init__(self, root):
    self.root = root
    self.root.title("SOBEK Khal Network Updater - Developed by Arafat Kabir")
    self.root.geometry("1240x780")

    self.ntw_path = tk.StringVar()
    self.shp_path = tk.StringVar()
    self.out_ntw_path = tk.StringVar()
    self.prefix_var = tk.StringVar(value="K41_")
    self.snap_tol_var = tk.StringVar(value="1.5")
    self.min_len_var = tk.StringVar(value="2.0")
    self.branch_id_start_var = tk.StringVar(value="500")
    self.show_bg_ntw_var = tk.BooleanVar(value=True)
    self.add_boundary_var = tk.BooleanVar(value=True)
    self.replace_existing_prefix_var = tk.BooleanVar(value=True)

    self.generated_lines = []
    self.node_table_rows = []
    self.khal_reach_items = []
    self.bg_points = []
    self.selected_node_id = None

    self._build_ui()

  def _build_ui(self):
    footer = ttk.Frame(self.root, padding=(10, 4))
    footer.pack(side="bottom", fill="x")
    ttk.Label(footer, text=REPO_URL, font=("Segoe UI", 8)).pack(side="left")
    ttk.Label(
        footer,
        text="Developed by Arafat Kabir",
        font=("Segoe UI", 9, "italic"),
    ).pack(side="right")

    top_frame = ttk.LabelFrame(
        self.root, text="1. Files & Parameters", padding=8
    )
    top_frame.pack(fill="x", padx=10, pady=6)

    ttk.Label(top_frame, text="Existing network.ntw:").grid(
        row=0, column=0, sticky="w", pady=2
    )
    ttk.Entry(top_frame, textvariable=self.ntw_path, width=78).grid(
        row=0, column=1, padx=5
    )
    ttk.Button(top_frame, text="Browse NTW", command=self.browse_ntw).grid(
        row=0, column=2
    )

    ttk.Label(top_frame, text="Khal Shapefile (BTM):").grid(
        row=1, column=0, sticky="w", pady=2
    )
    ttk.Entry(top_frame, textvariable=self.shp_path, width=78).grid(
        row=1, column=1, padx=5
    )
    ttk.Button(top_frame, text="Browse SHP", command=self.browse_shp).grid(
        row=1, column=2
    )

    ttk.Label(top_frame, text="Output network.ntw:").grid(
        row=2, column=0, sticky="w", pady=2
    )
    ttk.Entry(top_frame, textvariable=self.out_ntw_path, width=78).grid(
        row=2, column=1, padx=5
    )
    ttk.Button(top_frame, text="Save As...", command=self.browse_out).grid(
        row=2, column=2
    )

    opt_frame = ttk.Frame(top_frame)
    opt_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=5)

    ttk.Label(opt_frame, text="Prefix:").pack(side="left")
    ttk.Entry(opt_frame, textvariable=self.prefix_var, width=8).pack(
        side="left", padx=(2, 10)
    )

    ttk.Label(opt_frame, text="Snap (m):").pack(side="left")
    ttk.Entry(opt_frame, textvariable=self.snap_tol_var, width=6).pack(
        side="left", padx=(2, 10)
    )

    ttk.Label(opt_frame, text="Min Len (m):").pack(side="left")
    ttk.Entry(opt_frame, textvariable=self.min_len_var, width=6).pack(
        side="left", padx=(2, 10)
    )

    ttk.Label(opt_frame, text="Start Branch:").pack(side="left")
    ttk.Entry(opt_frame, textvariable=self.branch_id_start_var, width=7).pack(
        side="left", padx=(2, 10)
    )

    ttk.Checkbutton(
        opt_frame,
        text="Boundary Nodes",
        variable=self.add_boundary_var,
        command=self.draw_map,
    ).pack(side="left", padx=5)
    ttk.Checkbutton(
        opt_frame,
        text="Show Existing NTW BG",
        variable=self.show_bg_ntw_var,
        command=self.draw_map,
    ).pack(side="left", padx=5)
    ttk.Checkbutton(
        opt_frame,
        text="Replace same Prefix",
        variable=self.replace_existing_prefix_var,
    ).pack(side="left", padx=5)

    btn_frame = ttk.Frame(self.root)
    btn_frame.pack(fill="x", padx=10, pady=3)

    ttk.Button(
        btn_frame,
        text="Generate & Preview Khal",
        command=self.process_and_merge,
    ).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="Refresh Map", command=self.draw_map).pack(
        side="left", padx=4
    )
    ttk.Button(
        btn_frame,
        text="Save Updated NTW File",
        command=self.save_updated_ntw,
    ).pack(side="left", padx=4)

    paned = ttk.PanedWindow(self.root, orient="horizontal")
    paned.pack(fill="both", expand=True, padx=10, pady=6)

    map_frame = ttk.LabelFrame(
        paned, text="2. Visual Map (Mouse Scroll to Zoom)", padding=6
    )
    paned.add(map_frame, weight=3)

    self.fig, self.ax = plt.subplots(figsize=(6.5, 5.5))
    self.canvas = FigureCanvasTkAgg(self.fig, master=map_frame)
    self.canvas.get_tk_widget().pack(fill="both", expand=True)
    self.canvas.mpl_connect("pick_event", self.on_map_pick)
    self.canvas.mpl_connect("scroll_event", self.on_scroll_zoom)

    toolbar = NavigationToolbar2Tk(self.canvas, map_frame)
    toolbar.update()

    right_nb = ttk.Notebook(paned)
    paned.add(right_nb, weight=2)

    node_tab = ttk.Frame(right_nb, padding=6)
    right_nb.add(node_tab, text="3. Khal Nodes Table")

    ctrl_bar = ttk.Frame(node_tab)
    ctrl_bar.pack(fill="x", pady=(0, 5))

    self.type_combo = ttk.Combobox(
        ctrl_bar,
        values=["SBK_CHANNELCONNECTION", "SBK_BOUNDARY", "SBK_GRIDPOINT"],
        width=22,
        state="readonly",
    )
    self.type_combo.set("SBK_CHANNELCONNECTION")
    self.type_combo.pack(side="left", padx=2)

    ttk.Button(
        ctrl_bar, text="Change Type", command=self.apply_node_type_change
    ).pack(side="left", padx=2)
    ttk.Button(
        ctrl_bar, text="Delete", command=self.delete_selected_node
    ).pack(side="left", padx=2)
    ttk.Button(
        ctrl_bar, text="Sync NTW", command=self.rebuild_ntw_lines_from_nodes
    ).pack(side="left", padx=2)

    cols = ("Node_ID", "Node_Type", "X_BTM", "Y_BTM", "Conn")
    self.tree = ttk.Treeview(
        node_tab, columns=cols, show="headings", height=18
    )
    widths = {
        "Node_ID": 95,
        "Node_Type": 165,
        "X_BTM": 95,
        "Y_BTM": 95,
        "Conn": 50,
    }
    for c in cols:
      self.tree.heading(c, text=c)
      self.tree.column(c, width=widths[c], anchor="center")
    self.tree.pack(fill="both", expand=True)
    self.tree.bind("<<TreeviewSelect>>", self.on_table_select)

    log_tab = ttk.Frame(right_nb, padding=6)
    right_nb.add(log_tab, text="4. Log")
    self.log_box = scrolledtext.ScrolledText(log_tab, height=15)
    self.log_box.pack(fill="both", expand=True)

  def on_scroll_zoom(self, event):
    if event.inaxes != self.ax:
      return
    base_scale = 1.2
    if event.button == "up":
      scale_factor = 1 / base_scale
    elif event.button == "down":
      scale_factor = base_scale
    else:
      return

    xlim = self.ax.get_xlim()
    ylim = self.ax.get_ylim()
    xdata, ydata = event.xdata, event.ydata
    if xdata is None or ydata is None:
      return

    new_width = (xlim[1] - xlim[0]) * scale_factor
    new_height = (ylim[1] - ylim[0]) * scale_factor
    relx = (xlim[1] - xdata) / (xlim[1] - xlim[0])
    rely = (ylim[1] - ydata) / (ylim[1] - ylim[0])

    self.ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
    self.ax.set_ylim(
        [ydata - new_height * (1 - rely), ydata + new_height * rely]
    )
    self.canvas.draw_idle()

  def log(self, msg):
    self.log_box.insert(tk.END, msg + "\n")
    self.log_box.see(tk.END)
    self.root.update_idletasks()

  def browse_ntw(self):
    p = filedialog.askopenfilename(
        filetypes=[("SOBEK Network File", "*.ntw"), ("All Files", "*.*")]
    )
    if p:
      self.ntw_path.set(p)
      if not self.out_ntw_path.get():
        base, ext = os.path.splitext(p)
        self.out_ntw_path.set(f"{base}_khal_updated{ext}")
      self._load_bg_ntw_coords(p)
      self.draw_map()

  def _load_bg_ntw_coords(self, ntw_file):
    self.bg_points = []
    try:
      with open(ntw_file, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f):
          if idx == 0 or not line.strip():
            continue
          parts = line.strip().split(",")
          for i in range(len(parts) - 1):
            try:
              x = float(parts[i])
              y = float(parts[i + 1])
              if 200000 < x < 900000 and 200000 < y < 1000000:
                self.bg_points.append((x, y))
            except ValueError:
              continue
      self.log(f"Loaded {len(self.bg_points)} background NTW points.")
    except Exception as e:
      self.log(f"BG NTW read warning: {e}")

  def browse_shp(self):
    p = filedialog.askopenfilename(
        filetypes=[("Shapefile", "*.shp"), ("All Files", "*.*")]
    )
    if p:
      self.shp_path.set(p)

  def browse_out(self):
    p = filedialog.asksaveasfilename(
        defaultextension=".ntw", filetypes=[("SOBEK Network File", "*.ntw")]
    )
    if p:
      self.out_ntw_path.set(p)

  def _format_ntw_row(
      self,
      reach_id,
      branch_id,
      length_m,
      from_id,
      from_type,
      fx,
      fy,
      to_id,
      to_type,
      tx,
      ty,
  ):
    code_map = {
        "SBK_CHANNELCONNECTION": 12,
        "SBK_BOUNDARY": 14,
        "SBK_GRIDPOINT": 16,
    }
    c1 = code_map.get(from_type, 12)
    c2 = code_map.get(to_type, 12)
    return (
        f'"{reach_id}","", {branch_id},1,"SBK_CHANNEL","",0,0,0,0,{length_m},0,0,0,'
        f'"{from_id}","","",0,{c1},"{from_type}",,{fx},{fy},0,0,"SYS_DEFAULT",0,'
        f'"{to_id}","","",0,{c2},"{to_type}",,{tx},{ty},0,{length_m},"SYS_DEFAULT",0\n'
    )

  def process_and_merge(self):
    ntw_file = self.ntw_path.get().strip()
    shp_file = self.shp_path.get().strip()

    if not ntw_file or not os.path.exists(ntw_file):
      messagebox.showerror("Error", "Select a valid existing network.ntw")
      return
    if not shp_file or not os.path.exists(shp_file):
      messagebox.showerror("Error", "Select a valid Khal Shapefile (.shp)")
      return

    try:
      snap_tol = float(self.snap_tol_var.get())
      min_len = float(self.min_len_var.get())
      branch_start = int(self.branch_id_start_var.get())
    except ValueError:
      messagebox.showerror(
          "Error", "Enter valid numbers for Snap, Min Len, and Start Branch"
      )
      return

    prefix = self.prefix_var.get().strip() or "K_"
    self.log("Processing Khal Shapefile...")

    gdf = gpd.read_file(shp_file)
    gdf = gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty].copy()
    gdf = gdf.explode(index_parts=False)

    union_geom = unary_union(gdf.geometry.tolist())
    snapped_geom = snap(union_geom, union_geom, snap_tol)
    split_geom = unary_union(snapped_geom)
    merged_geom = linemerge(split_geom)
    final_geom = unary_union(merged_geom)

    lines = []
    if final_geom.geom_type == "LineString":
      lines = [final_geom]
    elif final_geom.geom_type == "MultiLineString":
      lines = list(final_geom.geoms)

    def norm_pt(pt):
      return (round(pt[0], 1), round(pt[1], 1))

    raw_reaches = []
    endpoints = []

    for line in lines:
      if line.length < min_len:
        continue
      p1 = norm_pt(line.coords[0])
      p2 = norm_pt(line.coords[-1])
      if p1 == p2:
        continue
      raw_reaches.append((line.coords[0], line.coords[-1], p1, p2, line.length))
      endpoints.extend([p1, p2])

    counts = Counter(endpoints)
    coord_to_node = {}
    self.node_table_rows = []
    cn_i, bn_i = 1, 1

    for coord, cnt in counts.items():
      if cnt >= 3:
        nid = f"{prefix}CN_{cn_i:03d}"
        ntype = "SBK_CHANNELCONNECTION"
        cn_i += 1
      elif cnt == 1 and self.add_boundary_var.get():
        nid = f"{prefix}BN_{bn_i:03d}"
        ntype = "SBK_BOUNDARY"
        bn_i += 1
      else:
        continue
      coord_to_node[coord] = [nid, ntype, coord[0], coord[1], cnt]
      self.node_table_rows.append([nid, ntype, coord[0], coord[1], cnt])

    self.khal_reach_items = []
    r_i = 1
    for c_start, c_end, p1, p2, length in raw_reaches:
      if p1 not in coord_to_node:
        nid = f"{prefix}N_{r_i:03d}_A"
        ntype = "SBK_CHANNELCONNECTION"
        coord_to_node[p1] = [nid, ntype, c_start[0], c_start[1], counts[p1]]
        self.node_table_rows.append(
            [nid, ntype, c_start[0], c_start[1], counts[p1]]
        )
      if p2 not in coord_to_node:
        nid = f"{prefix}N_{r_i:03d}_B"
        ntype = "SBK_CHANNELCONNECTION"
        coord_to_node[p2] = [nid, ntype, c_end[0], c_end[1], counts[p2]]
        self.node_table_rows.append(
            [nid, ntype, c_end[0], c_end[1], counts[p2]]
        )

      rid = f"{prefix}R_{r_i:03d}"
      bid = branch_start + r_i
      self.khal_reach_items.append({
          "reach_id": rid,
          "branch_id": bid,
          "length": round(length, 4),
          "p1": p1,
          "p2": p2,
          "c1": c_start,
          "c2": c_end,
      })
      r_i += 1

    self._refresh_tree()
    self.rebuild_ntw_lines_from_nodes()
    self.draw_map()
    self.log(
        f"Nodes: {len(self.node_table_rows)} | Reaches:"
        f" {len(self.khal_reach_items)}"
    )

  def _refresh_tree(self):
    for item in self.tree.get_children():
      self.tree.delete(item)
    for row in self.node_table_rows:
      iid = self.tree.insert("", "end", values=row)
      if self.selected_node_id and row[0] == self.selected_node_id:
        self.tree.selection_set(iid)
        self.tree.see(iid)

  def on_table_select(self, event):
    sel = self.tree.selection()
    if sel:
      vals = self.tree.item(sel[0])["values"]
      self.selected_node_id = vals[0]
      self.type_combo.set(vals[1])
      self.draw_map(preserve_limits=True)

  def on_map_pick(self, event):
    if hasattr(event.artist, "node_ids"):
      idx = event.ind[0]
      nid = event.artist.node_ids[idx]
      self.selected_node_id = nid
      self._refresh_tree()
      for row in self.node_table_rows:
        if row[0] == nid:
          self.type_combo.set(row[1])
          self.log(f"Picked: {nid} ({row[1]}) at ({row[2]}, {row[3]})")
          break
      self.draw_map(preserve_limits=True)

  def draw_map(self, preserve_limits=False):
    prev_xlim = self.ax.get_xlim() if preserve_limits else None
    prev_ylim = self.ax.get_ylim() if preserve_limits else None
    has_data_drawn = bool(self.ax.lines or self.ax.collections)

    self.ax.clear()

    if self.show_bg_ntw_var.get() and self.bg_points:
      bg_sub = self.bg_points[::5]
      bx = [p[0] for p in bg_sub]
      by = [p[1] for p in bg_sub]
      self.ax.scatter(
          bx,
          by,
          s=6,
          c="#cbd5e1",
          alpha=0.5,
          label="Existing NTW",
          zorder=1,
      )

    for idx, r in enumerate(self.khal_reach_items):
      x1, y1 = r["c1"][0], r["c1"][1]
      x2, y2 = r["c2"][0], r["c2"][1]
      self.ax.plot(
          [x1, x2],
          [y1, y2],
          color="#2563eb",
          linewidth=1.6,
          label="Khal Reaches" if idx == 0 else "",
          zorder=2,
      )

    cn_x, cn_y, cn_ids = [], [], []
    bn_x, bn_y, bn_ids = [], [], []
    gp_x, gp_y, gp_ids = [], [], []
    sel_pt = None

    for nid, ntype, x, y, cnt in self.node_table_rows:
      if self.selected_node_id == nid:
        sel_pt = (x, y, nid, ntype)
      if ntype == "SBK_CHANNELCONNECTION":
        cn_x.append(x)
        cn_y.append(y)
        cn_ids.append(nid)
      elif ntype == "SBK_BOUNDARY":
        bn_x.append(x)
        bn_y.append(y)
        bn_ids.append(nid)
      else:
        gp_x.append(x)
        gp_y.append(y)
        gp_ids.append(nid)

    if cn_x:
      sc_cn = self.ax.scatter(
          cn_x,
          cn_y,
          s=42,
          c="#ec4899",
          marker="o",
          edgecolors="black",
          linewidths=0.6,
          picker=5,
          label="Connection",
          zorder=3,
      )
      sc_cn.node_ids = cn_ids

    if bn_x:
      sc_bn = self.ax.scatter(
          bn_x,
          bn_y,
          s=55,
          c="#facc15",
          marker="s",
          edgecolors="black",
          linewidths=0.8,
          picker=5,
          label="Boundary",
          zorder=4,
      )
      sc_bn.node_ids = bn_ids

    if gp_x:
      sc_gp = self.ax.scatter(
          gp_x,
          gp_y,
          s=35,
          c="#22c55e",
          marker="^",
          edgecolors="black",
          linewidths=0.6,
          picker=5,
          label="GridPoint",
          zorder=3,
      )
      sc_gp.node_ids = gp_ids

    if sel_pt:
      sx, sy, snid, sntype = sel_pt
      self.ax.scatter(
          [sx],
          [sy],
          s=220,
          facecolors="none",
          edgecolors="#ef4444",
          linewidths=2.5,
          zorder=6,
      )
      self.ax.annotate(
          f" {snid}\n ({sntype.replace('SBK_', '')})",
          (sx, sy),
          textcoords="offset points",
          xytext=(8, 8),
          fontsize=8.5,
          fontweight="bold",
          color="#991b1b",
          bbox=dict(
              boxstyle="round,pad=0.25",
              fc="#fef2f2",
              ec="#ef4444",
              alpha=0.92,
          ),
          zorder=7,
      )

    self.ax.set_title("Khal Network Schematisation Preview (BTM)")
    self.ax.set_xlabel("X (BTM m)")
    self.ax.set_ylabel("Y (BTM m)")
    self.ax.set_aspect("equal", adjustable="datalim")
    self.ax.grid(True, linestyle="--", alpha=0.35)
    if self.ax.get_legend_handles_labels()[0]:
      self.ax.legend(loc="best", fontsize=8)

    if preserve_limits and has_data_drawn and prev_xlim and prev_ylim:
      self.ax.set_xlim(prev_xlim)
      self.ax.set_ylim(prev_ylim)

    self.fig.tight_layout()
    self.canvas.draw()

  def apply_node_type_change(self):
    sel = self.tree.selection()
    if not sel:
      messagebox.showwarning("Warning", "Select at least one node first")
      return
    new_type = self.type_combo.get()
    selected_ids = {self.tree.item(s)["values"][0] for s in sel}

    for row in self.node_table_rows:
      if row[0] in selected_ids:
        row[1] = new_type

    self._refresh_tree()
    self.rebuild_ntw_lines_from_nodes()
    self.draw_map(preserve_limits=True)
    self.log(f"Updated {len(selected_ids)} node(s) -> {new_type}")

  def delete_selected_node(self):
    sel = self.tree.selection()
    if not sel:
      return
    selected_ids = {self.tree.item(s)["values"][0] for s in sel}
    self.node_table_rows = [
        r for r in self.node_table_rows if r[0] not in selected_ids
    ]
    self.selected_node_id = None
    self._refresh_tree()
    self.rebuild_ntw_lines_from_nodes()
    self.draw_map(preserve_limits=True)
    self.log(f"Deleted {len(selected_ids)} node(s).")

  def rebuild_ntw_lines_from_nodes(self):
    ntw_file = self.ntw_path.get().strip()
    if not ntw_file or not os.path.exists(ntw_file):
      return
    with open(ntw_file, "r", encoding="utf-8", errors="ignore") as f:
      existing_lines = f.readlines()

    prefix = self.prefix_var.get().strip() or "K_"
    if self.replace_existing_prefix_var.get():
      kept_lines = [
          ln
          for ln in existing_lines
          if not ln.lstrip().startswith(f'"{prefix}')
      ]
    else:
      kept_lines = existing_lines

    coord_map = {}
    for nid, ntype, x, y, cnt in self.node_table_rows:
      coord_map[(round(x, 1), round(y, 1))] = (nid, ntype, x, y)

    new_khal_lines = []
    for reach in self.khal_reach_items:
      p1, p2 = reach["p1"], reach["p2"]
      if p1 not in coord_map or p2 not in coord_map:
        continue
      n1_id, n1_type, x1, y1 = coord_map[p1]
      n2_id, n2_type, x2, y2 = coord_map[p2]
      new_khal_lines.append(
          self._format_ntw_row(
              reach["reach_id"],
              reach["branch_id"],
              reach["length"],
              n1_id,
              n1_type,
              x1,
              y1,
              n2_id,
              n2_type,
              x2,
              y2,
          )
      )

    if not kept_lines or not kept_lines[0].startswith('"NTW6.6"'):
      kept_lines = [HEADER_LINE] + kept_lines

    self.generated_lines = kept_lines + new_khal_lines
    self.log(f"Synced {len(new_khal_lines)} Khal reach rows into NTW buffer.")

  def save_updated_ntw(self):
    if not self.generated_lines:
      messagebox.showwarning("Warning", "Run Generate & Preview Khal first")
      return
    out_path = self.out_ntw_path.get().strip()
    if not out_path:
      messagebox.showerror("Error", "Specify output .ntw path")
      return

    src_ntw = self.ntw_path.get().strip()
    if os.path.exists(src_ntw):
      bak_path = src_ntw + ".bak"
      if not os.path.exists(bak_path):
        shutil.copy2(src_ntw, bak_path)
        self.log(f"Backup created: {bak_path}")

    with open(out_path, "w", encoding="utf-8", newline="") as f:
      f.writelines(self.generated_lines)

    self.log(f"Saved: {out_path}")
    messagebox.showinfo("Success", f"Saved updated network.ntw:\n{out_path}")


if __name__ == "__main__":
  root = tk.Tk()
  app = SOBEKKhalUpdaterVisualApp(root)
  root.mainloop()
