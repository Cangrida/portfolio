bl_info = {
    "name": "Unreal Bridge",
    "author": "Claude",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "3D-вид > боковая панель (N) > Unreal",
    "description": "Экспорт в Unreal Engine: верный масштаб и оси, пивот, UCX-коллизия, скелетные меши и анимации, проверка перед отправкой",
    "category": "Import-Export",
}

import bpy
import bmesh
import os
import re
from bpy.props import (StringProperty, BoolProperty, EnumProperty,
                       FloatProperty, PointerProperty)
from mathutils import Vector


# ============================================================================
# НАСТРОЙКИ
# ============================================================================

class UB_Settings(bpy.types.PropertyGroup):

    export_dir: StringProperty(
        name="Папка",
        description="Куда складывать FBX. Эту же папку укажи в Unreal в Auto Reimport, "
                    "тогда правки будут приезжать сами. // в начале означает «рядом с .blend»",
        subtype='DIR_PATH',
        default="//UE_export/",
    )
    asset_type: EnumProperty(
        name="Тип",
        description="Что экспортируем",
        items=[
            ('STATIC', "Статик-меш", "Обычная геометрия: окружение, реквизит, модули"),
            ('SKELETAL', "Скелетный меш", "Меш с арматурой. Можно приложить анимацию"),
        ],
        default='STATIC',
    )
    prefix_static: StringProperty(name="Префикс", default="SM_")
    prefix_skeletal: StringProperty(name="Префикс", default="SK_")

    # --- группировка ---
    group_mode: EnumProperty(
        name="Группировка",
        description="Как раскладывать выделенное по файлам",
        items=[
            ('PER_OBJECT', "Объект = файл", "Каждый объект отдельным FBX. Так делают модули и реквизит"),
            ('PER_COLLECTION', "Коллекция = файл", "Все объекты коллекции в один FBX"),
            ('SINGLE', "Всё в один файл", "Вся выборка одним FBX с сохранением взаимного расположения"),
        ],
        default='PER_OBJECT',
    )
    single_name: StringProperty(name="Имя файла", default="Scene")

    # --- пивот ---
    pivot_mode: EnumProperty(
        name="Пивот",
        description="Где окажется точка отсчёта ассета в Unreal",
        items=[
            ('ORIGIN', "Origin объекта", "Origin как он есть, объект приедет в ноль"),
            ('BASE_CENTER', "Низ, по центру", "Центр нижней грани. Для домов, деревьев, бочек"),
            ('BASE_CORNER', "Низ, угол", "Угол нижней грани. Для стен, полов и всего, что по сетке"),
            ('WORLD', "Как стоит в сцене", "Не двигать. Для экспорта готовой сцены целиком"),
        ],
        default='BASE_CENTER',
    )

    # --- коллизия ---
    make_ucx: BoolProperty(
        name="Добавлять коллизию UCX",
        description="Unreal читает объект с именем UCX_<имя>_00 как коллизию. "
                    "Без неё движок лепит свою примерную или не делает никакой",
        default=True,
    )
    ucx_type: EnumProperty(
        name="Форма",
        items=[
            ('BOX', "Коробка", "Прямоугольник по габаритам. Дёшево, годится для зданий и ящиков"),
            ('CONVEX', "Выпуклая оболочка", "Плотнее обтягивает форму. Для башен, скал, бочек"),
        ],
        default='BOX',
    )
    ucx_shrink: FloatProperty(
        name="Поджать, м",
        description="Ужать коллизию внутрь, чтобы не выпирала за модель",
        default=0.0, min=0.0, max=2.0,
    )

    # --- анимация ---
    export_anim: BoolProperty(
        name="С анимацией",
        description="Запечь текущее действие в FBX",
        default=True,
    )

    # --- прочее ---
    apply_mods: BoolProperty(name="Применять модификаторы", default=True)
    smooth_type: EnumProperty(
        name="Сглаживание",
        items=[
            ('FACE', "По граням", "Сохраняет flat shading. Для low-poly обязательно"),
            ('EDGE', "По рёбрам", "Обычный вариант для сглаженных моделей"),
            ('OFF', "Не передавать", ""),
        ],
        default='FACE',
    )
    grid: FloatProperty(
        name="Сетка, м",
        description="Шаг модульной сетки. Проверка предупредит, если габариты не кратны",
        default=1.0, min=0.0,
    )
    check_before: BoolProperty(
        name="Проверять перед отправкой",
        default=True,
    )


# ============================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ============================================================================

def clean_name(name):
    name = re.sub(r'\.\d{3}$', '', name)
    name = re.sub(r'[^0-9A-Za-zА-Яа-я_\-]', '_', name)
    return name or "Asset"


def world_bounds(objs):
    pts = []
    for o in objs:
        pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    if not pts:
        return Vector(), Vector()
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def pivot_shift(objs, mode):
    """на сколько сдвинуть группу, чтобы нужная точка встала в мировой ноль"""
    if mode == 'WORLD':
        return Vector((0, 0, 0))
    if mode == 'ORIGIN':
        return -objs[0].matrix_world.translation
    mn, mx = world_bounds(objs)
    if mode == 'BASE_CENTER':
        p = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    else:
        p = Vector((mn.x, mn.y, mn.z))
    return -p


def build_ucx(obj, base_name, kind, shrink):
    """объект-коллизия по форме obj"""
    if kind == 'BOX':
        mn, mx = world_bounds([obj])
        lo = Vector((mn.x + shrink, mn.y + shrink, mn.z + shrink))
        hi = Vector((mx.x - shrink, mx.y - shrink, mx.z - shrink))
        for i in range(3):
            if hi[i] <= lo[i]:
                lo[i], hi[i] = mn[i], mx[i]
        bm = bmesh.new()
        v = [
            bm.verts.new((lo.x, lo.y, lo.z)), bm.verts.new((hi.x, lo.y, lo.z)),
            bm.verts.new((hi.x, hi.y, lo.z)), bm.verts.new((lo.x, hi.y, lo.z)),
            bm.verts.new((lo.x, lo.y, hi.z)), bm.verts.new((hi.x, lo.y, hi.z)),
            bm.verts.new((hi.x, hi.y, hi.z)), bm.verts.new((lo.x, hi.y, hi.z)),
        ]
        for f in [(0,1,2,3), (4,7,6,5), (0,4,5,1), (1,5,6,2), (2,6,7,3), (3,7,4,0)]:
            bm.faces.new([v[i] for i in f])
    else:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        src = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(src)
        ev.to_mesh_clear()
        bm.transform(obj.matrix_world)
        bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if not f.is_valid], context='FACES')
        if shrink > 0 and len(bm.verts):
            c = sum((vv.co for vv in bm.verts), Vector()) / len(bm.verts)
            for vv in bm.verts:
                d = vv.co - c
                if d.length > shrink:
                    vv.co = c + d.normalized() * (d.length - shrink)

    me = bpy.data.meshes.new("UCX_tmp")
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ucx = bpy.data.objects.new("UCX_%s_00" % base_name, me)
    bpy.context.collection.objects.link(ucx)
    return ucx


def fbx_args(s):
    """настройки, при которых Unreal читает файл правильно.
    global_scale=1 и apply_unit_scale=True вместе дают метры -> сантиметры один раз."""
    a = dict(
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        axis_forward='-Y',
        axis_up='Z',
        use_mesh_modifiers=s.apply_mods,
        mesh_smooth_type=s.smooth_type,
        use_triangles=False,
        bake_space_transform=False,
        add_leaf_bones=False,
        path_mode='COPY',
    )
    if s.asset_type == 'SKELETAL':
        a['object_types'] = {'MESH', 'ARMATURE'}
        a['primary_bone_axis'] = 'Y'
        a['secondary_bone_axis'] = 'X'
        a['bake_anim'] = s.export_anim
        a['bake_anim_use_all_bones'] = True
        a['bake_anim_use_nla_strips'] = False
        a['bake_anim_use_all_actions'] = False
        a['bake_anim_force_startend_keying'] = True
        a['bake_anim_step'] = 1.0
        a['bake_anim_simplify_factor'] = 0.0
    else:
        a['object_types'] = {'MESH'}
        a['bake_anim'] = False
    return a


def collect_problems(objs, s):
    out = []
    for o in objs:
        if o.type != 'MESH':
            continue
        if any(abs(v - 1.0) > 1e-3 for v in o.scale):
            out.append("%s: масштаб не применён (%.2f, %.2f, %.2f) — Ctrl+A > Scale"
                       % (o.name, o.scale.x, o.scale.y, o.scale.z))
        if o.scale.x * o.scale.y * o.scale.z < 0:
            out.append("%s: отрицательный масштаб — нормали вывернутся" % o.name)
        if not o.data.uv_layers:
            out.append("%s: нет UV-развёртки — текстуры не лягут" % o.name)

        bm = bmesh.new()
        bm.from_mesh(o.data)
        open_e = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        loose = sum(1 for v in bm.verts if not v.link_edges)
        ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
        bm.free()
        if open_e:
            out.append("%s: %d незамкнутых рёбер — поверхность без толщины, коллизия может протекать"
                       % (o.name, open_e))
        if loose:
            out.append("%s: %d висящих вершин" % (o.name, loose))
        if ngons:
            out.append("%s: %d n-гонов — Unreal триангулирует по-своему" % (o.name, ngons))

        if s.grid > 0:
            bad = []
            for axis, d in zip("XYZ", o.dimensions):
                r = d / s.grid
                if abs(r - round(r)) * s.grid > 0.05:
                    bad.append("%s=%.2f" % (axis, d))
            if bad:
                out.append("%s: габариты не кратны сетке %.2f м (%s)"
                           % (o.name, s.grid, ", ".join(bad)))
    return out


# ============================================================================
# ОПЕРАТОРЫ
# ============================================================================

class UB_OT_check(bpy.types.Operator):
    bl_idname = "ub.check"
    bl_label = "Проверить выделенное"
    bl_description = "Ищет то, что обычно ломает перенос: неприменённый масштаб, дыры, отсутствие UV, отход от сетки"

    def execute(self, context):
        s = context.scene.ub_settings
        objs = [o for o in context.selected_objects if o.type == 'MESH']
        if not objs:
            self.report({'WARNING'}, "Ничего не выделено")
            return {'CANCELLED'}
        problems = collect_problems(objs, s)
        if problems:
            print("\n=== Unreal Bridge: проверка ===")
            for p in problems:
                print(" -", p)
            for p in problems[:8]:
                self.report({'WARNING'}, p)
            self.report({'WARNING'}, "Замечаний: %d (весь список — в системной консоли)" % len(problems))
        else:
            self.report({'INFO'}, "Чисто: %d объектов готовы" % len(objs))
        return {'FINISHED'}


class UB_OT_export(bpy.types.Operator):
    bl_idname = "ub.export"
    bl_label = "Отправить в Unreal"
    bl_description = "Экспорт FBX с настройками, которые Unreal читает без правки масштаба"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.ub_settings
        sel = [o for o in context.selected_objects if o.type in {'MESH', 'ARMATURE'}]
        if not sel:
            self.report({'WARNING'}, "Ничего не выделено")
            return {'CANCELLED'}

        if s.check_before:
            problems = collect_problems([o for o in sel if o.type == 'MESH'], s)
            if problems:
                print("\n=== Unreal Bridge: замечания перед экспортом ===")
                for p in problems:
                    print(" -", p)
                self.report({'WARNING'}, "Есть %d замечаний, смотри консоль. Экспорт всё равно выполнен"
                            % len(problems))

        folder = bpy.path.abspath(s.export_dir)
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            self.report({'ERROR'}, "Не удалось создать папку: %s" % e)
            return {'CANCELLED'}

        groups = self._make_groups(sel, s)
        active = context.view_layer.objects.active
        saved = [(o, o.matrix_world.copy()) for o in sel]
        written = []

        try:
            for name, objs in groups:
                written += self._export(context, name, objs, folder, s)
        finally:
            for o, mw in saved:
                o.matrix_world = mw
            bpy.ops.object.select_all(action='DESELECT')
            for o in sel:
                o.select_set(True)
            if active:
                context.view_layer.objects.active = active

        if written:
            print("\n=== Unreal Bridge: отправлено ===")
            for w in written:
                print(" ", w)
            self.report({'INFO'}, "Файлов: %d -> %s" % (len(written), folder))
        else:
            self.report({'WARNING'}, "Ничего не записано")
        return {'FINISHED'}

    def _make_groups(self, sel, s):
        if s.group_mode == 'SINGLE':
            return [(clean_name(s.single_name), sel)]
        if s.group_mode == 'PER_COLLECTION':
            buckets = {}
            for o in sel:
                key = o.users_collection[0].name if o.users_collection else "Loose"
                buckets.setdefault(clean_name(key), []).append(o)
            return list(buckets.items())
        # PER_OBJECT: арматура едет вместе со своим мешем
        groups = []
        used = set()
        for o in sel:
            if o in used:
                continue
            if o.type == 'MESH':
                pack = [o]
                arm = o.find_armature()
                if arm and s.asset_type == 'SKELETAL':
                    pack.append(arm)
                    used.add(arm)
                used.add(o)
                groups.append((clean_name(o.name), pack))
        return groups

    def _export(self, context, base, objs, folder, s):
        prefix = s.prefix_skeletal if s.asset_type == 'SKELETAL' else s.prefix_static
        path = os.path.join(folder, "%s%s.fbx" % (prefix, base))

        shift = pivot_shift([o for o in objs if o.type == 'MESH'] or objs, s.pivot_mode)
        if shift.length > 0:
            for o in objs:
                if o.parent in objs:
                    continue
                o.matrix_world.translation = o.matrix_world.translation + shift
            context.view_layer.update()

        temp = []
        if s.make_ucx and s.asset_type == 'STATIC':
            for o in objs:
                if o.type != 'MESH':
                    continue
                try:
                    temp.append(build_ucx(o, clean_name(o.name), s.ucx_type, s.ucx_shrink))
                except Exception as e:
                    print("Unreal Bridge: коллизия для %s не создана — %s" % (o.name, e))

        bpy.ops.object.select_all(action='DESELECT')
        for o in objs + temp:
            o.select_set(True)
        context.view_layer.objects.active = objs[0]

        result = []
        try:
            bpy.ops.export_scene.fbx(filepath=path, **fbx_args(s))
            result.append(path)
        except Exception as e:
            self.report({'ERROR'}, "Ошибка экспорта %s: %s" % (os.path.basename(path), e))

        for t in temp:
            bpy.data.objects.remove(t, do_unlink=True)
        return result


class UB_OT_open_folder(bpy.types.Operator):
    bl_idname = "ub.open_folder"
    bl_label = "Открыть папку"

    def execute(self, context):
        folder = bpy.path.abspath(context.scene.ub_settings.export_dir)
        if os.path.isdir(folder):
            bpy.ops.wm.path_open(filepath=folder)
        else:
            self.report({'WARNING'}, "Папка появится после первого экспорта")
        return {'FINISHED'}


# ============================================================================
# ПАНЕЛЬ
# ============================================================================

class UB_PT_panel(bpy.types.Panel):
    bl_label = "Unreal Bridge"
    bl_idname = "UB_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Unreal"

    def draw(self, context):
        lay = self.layout
        s = context.scene.ub_settings

        lay.prop(s, "asset_type", expand=True)

        col = lay.column(align=True)
        col.prop(s, "export_dir")
        row = col.row(align=True)
        row.prop(s, "prefix_skeletal" if s.asset_type == 'SKELETAL' else "prefix_static")
        row.operator("ub.open_folder", text="", icon='FILE_FOLDER')

        box = lay.box()
        box.label(text="Раскладка по файлам", icon='FILE_3D')
        box.prop(s, "group_mode", text="")
        if s.group_mode == 'SINGLE':
            box.prop(s, "single_name")

        box = lay.box()
        box.label(text="Пивот", icon='PIVOT_BOUNDBOX')
        box.prop(s, "pivot_mode", text="")

        if s.asset_type == 'STATIC':
            box = lay.box()
            box.label(text="Коллизия", icon='MESH_CUBE')
            box.prop(s, "make_ucx")
            sub = box.column(align=True)
            sub.enabled = s.make_ucx
            sub.prop(s, "ucx_type", text="")
            sub.prop(s, "ucx_shrink")
        else:
            box = lay.box()
            box.label(text="Анимация", icon='ARMATURE_DATA')
            box.prop(s, "export_anim")

        box = lay.box()
        box.label(text="Прочее", icon='SETTINGS')
        box.prop(s, "smooth_type", text="Сглаживание")
        box.prop(s, "apply_mods")
        box.prop(s, "grid")
        box.prop(s, "check_before")

        sel = len([o for o in context.selected_objects if o.type in {'MESH', 'ARMATURE'}])
        lay.separator()
        lay.operator("ub.check", icon='CHECKMARK')
        big = lay.column()
        big.scale_y = 1.6
        big.enabled = sel > 0
        big.operator("ub.export", icon='EXPORT',
                     text="Отправить в Unreal (%d)" % sel if sel else "Ничего не выделено")

        lay.separator()
        col = lay.column(align=True)
        col.scale_y = 0.8
        col.label(text="В Unreal один раз включи")
        col.label(text="Auto Reimport на эту папку —")
        col.label(text="правки будут приезжать сами.")


classes = (UB_Settings, UB_OT_check, UB_OT_export, UB_OT_open_folder, UB_PT_panel)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.ub_settings = PointerProperty(type=UB_Settings)


def unregister():
    if hasattr(bpy.types.Scene, "ub_settings"):
        del bpy.types.Scene.ub_settings
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
