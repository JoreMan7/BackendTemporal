# Backend/routes/estadisticas.py
"""
Módulo de ESTADÍSTICAS Y REPORTES - GESTIÓN ECLESIAL

Endpoints:
- /api/estadisticas/resumen/      -> Dashboard global
- /api/estadisticas/habitantes/   -> Detalle Habitantes
- /api/estadisticas/citas/        -> Detalle Citas
- /api/estadisticas/grupos/       -> Detalle Grupos de Ayudantes / Tareas
- /api/estadisticas/finanzas/     -> Detalle Finanzas (movimientos de caja)
"""
"""
Módulo de ESTADÍSTICAS Y REPORTES - GESTIÓN ECLESIAL
Versión completa con todas las funcionalidades para estadísticas de habitantes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from database import execute_query
from utils import require_rol
from datetime import datetime, timedelta, date
import calendar

estadisticas_bp = Blueprint('estadisticas', __name__)

# ====================================================
# FUNCIONES AUXILIARES
# ====================================================

def obtener_rango_fechas(filtros):
    """Obtiene rango de fechas desde los filtros"""
    hoy = datetime.now().date()
    
    if filtros.get('tipo_rango') == 'personalizado':
        desde = filtros.get('fecha_inicio')
        hasta = filtros.get('fecha_fin')
        if desde and hasta:
            return datetime.strptime(desde, '%Y-%m-%d').date(), datetime.strptime(hasta, '%Y-%m-%d').date()
    
    if filtros.get('tipo_rango') == 'semana':
        return hoy - timedelta(days=7), hoy
    if filtros.get('tipo_rango') == '15dias':
        return hoy - timedelta(days=15), hoy
    if filtros.get('tipo_rango') == '30dias':
        return hoy - timedelta(days=30), hoy
    if filtros.get('tipo_rango') == 'trimestre':
        return hoy - timedelta(days=90), hoy
    if filtros.get('tipo_rango') == 'semestre':
        return hoy - timedelta(days=180), hoy
    if filtros.get('tipo_rango') == 'anio':
        return hoy.replace(month=1, day=1), hoy
    
    # Por defecto: mes actual
    inicio_mes = hoy.replace(day=1)
    fin_mes = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])
    return inicio_mes, fin_mes

def calcular_variacion(actual, anterior):
    """Calcula variación porcentual"""
    if anterior == 0:
        return 0
    return ((actual - anterior) / anterior) * 100

# ====================================================
# ENDPOINTS DE ESTADÍSTICAS DE HABITANTES
# ====================================================

@estadisticas_bp.route('/habitantes/kpis/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_kpis_habitantes():
    """
    KPIs generales de habitantes con crecimiento comparativo
    Retorna:
    - totalHabitantes, totalFamilias, conSacramento, sinSacramento
    - sectorMayor, sectorMenor (con nombre y cantidad)
    - crecimiento porcentual vs período anterior
    - distribución por edades
    """
    try:
        tipo_rango = request.args.get('tipo_rango', 'mes')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        filtros = {
            'tipo_rango': tipo_rango,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        
        desde, hasta = obtener_rango_fechas(filtros)
        
        # Calcular período anterior para comparación
        dias_periodo = (hasta - desde).days
        desde_anterior = desde - timedelta(days=dias_periodo)
        hasta_anterior = desde - timedelta(days=1)
        
        # ========== TOTAL HABITANTES (PERIODO ACTUAL) ==========
        total_actual = execute_query("""
            SELECT COUNT(*) as total 
            FROM habitantes 
            WHERE Activo = 1 
            AND FechaRegistro BETWEEN %s AND %s
        """, (desde, hasta), fetch_one=True)
        
        # ========== TOTAL HABITANTES (PERIODO ANTERIOR) ==========
        total_anterior = execute_query("""
            SELECT COUNT(*) as total 
            FROM habitantes 
            WHERE Activo = 1 
            AND FechaRegistro BETWEEN %s AND %s
        """, (desde_anterior, hasta_anterior), fetch_one=True)
        
        total_actual_val = total_actual['total'] if total_actual else 0
        total_anterior_val = total_anterior['total'] if total_anterior else 0
        crecimiento = calcular_variacion(total_actual_val, total_anterior_val)
        
        # ========== TOTAL FAMILIAS ==========
        total_familias = execute_query("""
            SELECT COUNT(DISTINCT IdGrupoFamiliar) as total 
            FROM habitantes 
            WHERE Activo = 1 
            AND FechaRegistro BETWEEN %s AND %s
            AND IdGrupoFamiliar IS NOT NULL
        """, (desde, hasta), fetch_one=True)
        
        # ========== CON SACRAMENTO ==========
        con_sacramento = execute_query("""
            SELECT COUNT(DISTINCT h.IdHabitante) as total
            FROM habitantes h
            INNER JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
            WHERE h.Activo = 1 
            AND h.FechaRegistro BETWEEN %s AND %s
        """, (desde, hasta), fetch_one=True)
        
        # ========== SIN SACRAMENTO ==========
        sin_sacramento = execute_query("""
            SELECT COUNT(*) as total
            FROM habitantes h
            WHERE h.Activo = 1 
            AND h.FechaRegistro BETWEEN %s AND %s
            AND NOT EXISTS (
                SELECT 1 FROM habitante_sacramento hs 
                WHERE hs.IdHabitante = h.IdHabitante
            )
        """, (desde, hasta), fetch_one=True)
        
        # ========== SECTOR CON MÁS HABITANTES ==========
        sector_mayor = execute_query("""
            SELECT 
                s.Descripcion as sector,
                COUNT(h.IdHabitante) as cantidad,
                ROUND((COUNT(h.IdHabitante) * 100.0 / (
                    SELECT COUNT(*) FROM habitantes 
                    WHERE Activo = 1 AND FechaRegistro BETWEEN %s AND %s
                )), 2) as porcentaje
            FROM habitantes h
            INNER JOIN sector s ON h.IdSector = s.IdSector
            WHERE h.Activo = 1 
            AND h.FechaRegistro BETWEEN %s AND %s
            GROUP BY h.IdSector, s.Descripcion
            ORDER BY cantidad DESC
            LIMIT 1
        """, (desde, hasta, desde, hasta), fetch_one=True)
        
        # ========== SECTOR CON MENOS HABITANTES ==========
        sector_menor = execute_query("""
            SELECT 
                s.Descripcion as sector,
                COUNT(h.IdHabitante) as cantidad,
                ROUND((COUNT(h.IdHabitante) * 100.0 / (
                    SELECT COUNT(*) FROM habitantes 
                    WHERE Activo = 1 AND FechaRegistro BETWEEN %s AND %s
                )), 2) as porcentaje
            FROM habitantes h
            INNER JOIN sector s ON h.IdSector = s.IdSector
            WHERE h.Activo = 1 
            AND h.FechaRegistro BETWEEN %s AND %s
            GROUP BY h.IdSector, s.Descripcion
            HAVING COUNT(h.IdHabitante) > 0
            ORDER BY cantidad ASC
            LIMIT 1
        """, (desde, hasta, desde, hasta), fetch_one=True)
        
        # ========== DISTRIBUCIÓN POR EDADES ==========
        distribucion_edades = execute_query("""
            SELECT 
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, FechaNacimiento, CURDATE()) BETWEEN 0 AND 12 THEN 1 ELSE 0 END) as ninos,
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, FechaNacimiento, CURDATE()) BETWEEN 13 AND 29 THEN 1 ELSE 0 END) as jovenes,
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, FechaNacimiento, CURDATE()) BETWEEN 30 AND 59 THEN 1 ELSE 0 END) as adultos,
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, FechaNacimiento, CURDATE()) >= 60 THEN 1 ELSE 0 END) as adultos_mayores
            FROM habitantes
            WHERE Activo = 1 
            AND FechaRegistro BETWEEN %s AND %s
        """, (desde, hasta), fetch_one=True)
        
        # ========== SACRAMENTOS MÁS COMUNES ==========
        sacramentos_comunes = execute_query("""
            SELECT 
                ts.Descripcion as sacramento,
                COUNT(*) as total,
                COUNT(DISTINCT h.IdSector) as sectores_afectados
            FROM habitante_sacramento hs
            INNER JOIN tiposacramentos ts ON hs.IdSacramento = ts.IdSacramento
            INNER JOIN habitantes h ON hs.IdHabitante = h.IdHabitante
            WHERE h.Activo = 1 
            AND h.FechaRegistro BETWEEN %s AND %s
            GROUP BY ts.IdSacramento, ts.Descripcion
            ORDER BY total DESC
            LIMIT 5
        """, (desde, hasta))
        
        return jsonify({
            'success': True,
            'filtros': {
                'desde': desde.isoformat(),
                'hasta': hasta.isoformat(),
                'tipo_rango': tipo_rango,
                'periodo_anterior_desde': desde_anterior.isoformat(),
                'periodo_anterior_hasta': hasta_anterior.isoformat()
            },
            'kpis': {
                'totalHabitantes': total_actual_val,
                'totalHabitantesAnterior': total_anterior_val,
                'crecimiento': round(crecimiento, 2),
                'totalFamilias': total_familias['total'] if total_familias else 0,
                'conSacramento': con_sacramento['total'] if con_sacramento else 0,
                'sinSacramento': sin_sacramento['total'] if sin_sacramento else 0,
                'sectorMayor': {
                    'sector': sector_mayor['sector'] if sector_mayor else 'N/A',
                    'cantidad': sector_mayor['cantidad'] if sector_mayor else 0,
                    'porcentaje': sector_mayor['porcentaje'] if sector_mayor else 0
                },
                'sectorMenor': {
                    'sector': sector_menor['sector'] if sector_menor else 'N/A',
                    'cantidad': sector_menor['cantidad'] if sector_menor else 0,
                    'porcentaje': sector_menor['porcentaje'] if sector_menor else 0
                },
                'distribucionEdades': {
                    'ninos': distribucion_edades['ninos'] if distribucion_edades else 0,
                    'jovenes': distribucion_edades['jovenes'] if distribucion_edades else 0,
                    'adultos': distribucion_edades['adultos'] if distribucion_edades else 0,
                    'adultos_mayores': distribucion_edades['adultos_mayores'] if distribucion_edades else 0
                },
                'sacramentosComunes': sacramentos_comunes
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener KPIs: {str(e)}'}), 500

@estadisticas_bp.route('/habitantes/por-sector/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_habitantes_por_sector():
    """
    Distribución detallada de habitantes por sector
    Incluye comparación con período anterior y variaciones
    """
    try:
        tipo_rango = request.args.get('tipo_rango', 'mes')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        filtros = {
            'tipo_rango': tipo_rango,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        
        desde, hasta = obtener_rango_fechas(filtros)
        
        # Calcular período anterior
        dias_periodo = (hasta - desde).days
        desde_anterior = desde - timedelta(days=dias_periodo)
        hasta_anterior = desde - timedelta(days=1)
        
        # ========== DISTRIBUCIÓN POR SECTOR (PERIODO ACTUAL) ==========
        sectores_actual = execute_query("""
            SELECT 
                s.IdSector,
                s.Descripcion as sector,
                COUNT(h.IdHabitante) as cantidad,
                ROUND((COUNT(h.IdHabitante) * 100.0 / (
                    SELECT COUNT(*) 
                    FROM habitantes 
                    WHERE Activo = 1 
                    AND FechaRegistro BETWEEN %s AND %s
                )), 2) as porcentaje,
                AVG(TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE())) as edad_promedio,
                COUNT(DISTINCT h.IdGrupoFamiliar) as familias,
                SUM(CASE WHEN h.TieneImpedimentoSalud = 1 THEN 1 ELSE 0 END) as con_impedimento
            FROM sector s
            LEFT JOIN habitantes h ON s.IdSector = h.IdSector 
                AND h.Activo = 1 
                AND h.FechaRegistro BETWEEN %s AND %s
            WHERE s.Activo = 1
            GROUP BY s.IdSector, s.Descripcion
            ORDER BY cantidad DESC, s.Descripcion
        """, (desde, hasta, desde, hasta))
        
        # ========== DISTRIBUCIÓN POR SECTOR (PERIODO ANTERIOR) ==========
        sectores_anterior = execute_query("""
            SELECT 
                s.IdSector,
                s.Descripcion as sector,
                COUNT(h.IdHabitante) as cantidad_anterior
            FROM sector s
            LEFT JOIN habitantes h ON s.IdSector = h.IdSector 
                AND h.Activo = 1 
                AND h.FechaRegistro BETWEEN %s AND %s
            WHERE s.Activo = 1
            GROUP BY s.IdSector, s.Descripcion
        """, (desde_anterior, hasta_anterior))
        
        # Crear diccionario para fácil acceso a datos anteriores
        sectores_anterior_dict = {s['IdSector']: s['cantidad_anterior'] for s in sectores_anterior}
        
        # ========== COMBINAR DATOS Y CALCULAR VARIACIONES ==========
        sectores_completos = []
        total_habitantes_actual = sum(s['cantidad'] for s in sectores_actual)
        
        for sector in sectores_actual:
            id_sector = sector['IdSector']
            cantidad_actual = sector['cantidad']
            cantidad_anterior = sectores_anterior_dict.get(id_sector, 0)
            variacion = calcular_variacion(cantidad_actual, cantidad_anterior)
            
            # Sacramentos por sector
            sacramentos_sector = execute_query("""
                SELECT 
                    COUNT(DISTINCT hs.IdHabitante) as con_sacramento,
                    GROUP_CONCAT(DISTINCT ts.Descripcion ORDER BY ts.Descripcion SEPARATOR ', ') as lista_sacramentos
                FROM habitantes h
                LEFT JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
                LEFT JOIN tiposacramentos ts ON hs.IdSacramento = ts.IdSacramento
                WHERE h.Activo = 1 
                AND h.IdSector = %s
                AND h.FechaRegistro BETWEEN %s AND %s
            """, (id_sector, desde, hasta), fetch_one=True)
            
            sectores_completos.append({
                'id': id_sector,
                'sector': sector['sector'],
                'cantidad': cantidad_actual,
                'porcentaje': round((cantidad_actual / total_habitantes_actual * 100), 2) if total_habitantes_actual > 0 else 0,
                'cantidad_anterior': cantidad_anterior,
                'variacion': round(variacion, 2),
                'edad_promedio': round(sector['edad_promedio'], 1) if sector['edad_promedio'] else 0,
                'familias': sector['familias'],
                'con_impedimento': sector['con_impedimento'],
                'con_sacramento': sacramentos_sector['con_sacramento'] if sacramentos_sector else 0,
                'lista_sacramentos': sacramentos_sector['lista_sacramentos'] if sacramentos_sector else 'Ninguno'
            })
        
        # Ordenar por cantidad descendente
        sectores_completos.sort(key=lambda x: x['cantidad'], reverse=True)
        
        return jsonify({
            'success': True,
            'periodo': {
                'actual': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
                'anterior': {'desde': desde_anterior.isoformat(), 'hasta': hasta_anterior.isoformat()}
            },
            'total_sectores': len(sectores_completos),
            'total_habitantes': total_habitantes_actual,
            'sectores': sectores_completos
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener distribución por sector: {str(e)}'}), 500

@estadisticas_bp.route('/habitantes/sacramentos-por-sector/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_sacramentos_por_sector():
    """
    Análisis detallado de sacramentos por sector
    Permite filtrar por sector y tipo de sacramento
    """
    try:
        tipo_rango = request.args.get('tipo_rango', 'mes')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        id_sector = request.args.get('id_sector', type=int)
        id_sacramento = request.args.get('id_sacramento', type=int)
        
        filtros = {
            'tipo_rango': tipo_rango,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        
        desde, hasta = obtener_rango_fechas(filtros)
        
        # ========== CONSTRUIR CONSULTA DINÁMICA ==========
        condiciones = ["h.Activo = 1", "h.FechaRegistro BETWEEN %s AND %s"]
        params = [desde, hasta]
        
        if id_sector:
            condiciones.append("h.IdSector = %s")
            params.append(id_sector)
        
        if id_sacramento:
            condiciones.append("hs.IdSacramento = %s")
            params.append(id_sacramento)
        
        where_clause = "WHERE " + " AND ".join(condiciones)
        
        # ========== SACRAMENTOS POR SECTOR ==========
        query = f"""
            SELECT 
                s.IdSector,
                s.Descripcion as sector,
                ts.IdSacramento,
                ts.Descripcion as sacramento,
                ts.Costo,
                COUNT(DISTINCT h.IdHabitante) as total_habitantes,
                COUNT(DISTINCT hs.IdHabitante) as total_con_sacramento,
                COUNT(DISTINCT CASE 
                    WHEN YEAR(hs.FechaSacramento) = YEAR(CURDATE()) 
                    THEN h.IdHabitante 
                END) as este_anio,
                COUNT(DISTINCT CASE 
                    WHEN YEAR(hs.FechaSacramento) = YEAR(CURDATE()) 
                    AND MONTH(hs.FechaSacramento) = MONTH(CURDATE()) 
                    THEN h.IdHabitante 
                END) as este_mes,
                COUNT(DISTINCT CASE 
                    WHEN YEAR(hs.FechaSacramento) = YEAR(CURDATE() - INTERVAL 1 MONTH)
                    AND MONTH(hs.FechaSacramento) = MONTH(CURDATE() - INTERVAL 1 MONTH) 
                    THEN h.IdHabitante 
                END) as mes_anterior,
                MIN(hs.FechaSacramento) as primera_fecha,
                MAX(hs.FechaSacramento) as ultima_fecha
            FROM sector s
            LEFT JOIN habitantes h ON s.IdSector = h.IdSector
            LEFT JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
            LEFT JOIN tiposacramentos ts ON hs.IdSacramento = ts.IdSacramento
            {where_clause}
            GROUP BY s.IdSector, s.Descripcion, ts.IdSacramento, ts.Descripcion, ts.Costo
            HAVING ts.IdSacramento IS NOT NULL
            ORDER BY s.Descripcion, ts.Descripcion
        """
        
        sacramentos_detalle = execute_query(query, tuple(params))
        
        # ========== RESUMEN POR SECTOR ==========
        resumen_por_sector = {}
        for item in sacramentos_detalle:
            sector_key = item['sector']
            if sector_key not in resumen_por_sector:
                resumen_por_sector[sector_key] = {
                    'sector': item['sector'],
                    'total_habitantes': item['total_habitantes'],
                    'total_sacramentos': 0,
                    'total_con_sacramento': 0,
                    'porcentaje_con_sacramento': 0,
                    'sacramentos_detalle': []
                }
            
            # Calcular variación mes a mes
            variacion_mensual = 0
            if item['mes_anterior'] > 0:
                variacion_mensual = calcular_variacion(item['este_mes'], item['mes_anterior'])
            
            resumen_por_sector[sector_key]['total_sacramentos'] += item['total_con_sacramento']
            resumen_por_sector[sector_key]['total_con_sacramento'] = item['total_con_sacramento']
            
            resumen_por_sector[sector_key]['sacramentos_detalle'].append({
                'sacramento': item['sacramento'],
                'costo': float(item['Costo']) if item['Costo'] else 0,
                'total': item['total_con_sacramento'],
                'este_anio': item['este_anio'],
                'este_mes': item['este_mes'],
                'mes_anterior': item['mes_anterior'],
                'variacion_mensual': round(variacion_mensual, 2),
                'primera_fecha': item['primera_fecha'].strftime('%Y-%m-%d') if item['primera_fecha'] else None,
                'ultima_fecha': item['ultima_fecha'].strftime('%Y-%m-%d') if item['ultima_fecha'] else None
            })
        
        # Calcular porcentajes
        for sector in resumen_por_sector.values():
            if sector['total_habitantes'] > 0:
                sector['porcentaje_con_sacramento'] = round(
                    (sector['total_con_sacramento'] / sector['total_habitantes']) * 100, 2
                )
        
        # ========== SACRAMENTOS MÁS COMUNES ==========
        sacramentos_comunes = execute_query("""
            SELECT 
                ts.Descripcion as sacramento,
                COUNT(*) as total,
                COUNT(DISTINCT h.IdSector) as sectores,
                ROUND(AVG(ts.Costo), 2) as costo_promedio
            FROM habitante_sacramento hs
            INNER JOIN tiposacramentos ts ON hs.IdSacramento = ts.IdSacramento
            INNER JOIN habitantes h ON hs.IdHabitante = h.IdHabitante
            WHERE h.Activo = 1 
            AND h.FechaRegistro BETWEEN %s AND %s
            GROUP BY ts.IdSacramento, ts.Descripcion
            ORDER BY total DESC
            LIMIT 10
        """, (desde, hasta))
        
        # ========== RESUMEN GENERAL ==========
        total_sacramentos = sum(item['total_con_sacramento'] for item in sacramentos_detalle)
        total_habitantes_con_sacramento = len(set(item['total_con_sacramento'] for item in sacramentos_detalle if item['total_con_sacramento'] > 0))
        
        return jsonify({
            'success': True,
            'filtros': {
                'id_sector': id_sector,
                'id_sacramento': id_sacramento,
                'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()}
            },
            'resumen_general': {
                'total_sacramentos': total_sacramentos,
                'total_habitantes_con_sacramento': total_habitantes_con_sacramento,
                'registros_analizados': len(sacramentos_detalle)
            },
            'sacramentos_comunes': sacramentos_comunes,
            'por_sector': list(resumen_por_sector.values()),
            'detalle_completo': sacramentos_detalle
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener sacramentos por sector: {str(e)}'}), 500

@estadisticas_bp.route('/habitantes/crecimiento-temporal/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_crecimiento_temporal():
    """
    Evolución del crecimiento de habitantes en el tiempo
    Puede ser por año, trimestre o mes
    """
    try:
        tipo_rango = request.args.get('tipo_rango', 'anio')
        cantidad_periodos = int(request.args.get('cantidad', 12))
        
        hoy = datetime.now()
        data = []
        
        if tipo_rango == 'mes':
            # Últimos N meses
            for i in range(cantidad_periodos - 1, -1, -1):
                fecha = hoy - timedelta(days=30*i)
                año = fecha.year
                mes = fecha.month
                
                # Calcular primer y último día del mes
                primer_dia = date(año, mes, 1)
                ultimo_dia = date(año, mes, calendar.monthrange(año, mes)[1])
                
                total = execute_query("""
                    SELECT COUNT(*) as total
                    FROM habitantes
                    WHERE Activo = 1
                    AND FechaRegistro BETWEEN %s AND %s
                """, (primer_dia, ultimo_dia), fetch_one=True)
                
                # Calcular crecimiento
                mes_anterior = primer_dia - timedelta(days=1)
                primer_dia_anterior = date(mes_anterior.year, mes_anterior.month, 1)
                ultimo_dia_anterior = date(mes_anterior.year, mes_anterior.month, calendar.monthrange(mes_anterior.year, mes_anterior.month)[1])
                
                total_anterior = execute_query("""
                    SELECT COUNT(*) as total
                    FROM habitantes
                    WHERE Activo = 1
                    AND FechaRegistro BETWEEN %s AND %s
                """, (primer_dia_anterior, ultimo_dia_anterior), fetch_one=True)
                
                crecimiento = calcular_variacion(
                    total['total'] if total else 0,
                    total_anterior['total'] if total_anterior else 0
                )
                
                data.append({
                    'periodo': f"{mes:02d}/{año}",
                    'fecha_inicio': primer_dia.isoformat(),
                    'fecha_fin': ultimo_dia.isoformat(),
                    'total': total['total'] if total else 0,
                    'total_anterior': total_anterior['total'] if total_anterior else 0,
                    'crecimiento': round(crecimiento, 2),
                    'tipo': 'mes'
                })
        
        elif tipo_rango == 'trimestre':
            # Últimos N trimestres
            for i in range(cantidad_periodos - 1, -1, -1):
                fecha_referencia = hoy - timedelta(days=90*i)
                año = fecha_referencia.year
                trimestre_num = ((fecha_referencia.month - 1) // 3) + 1
                
                # Calcular fechas del trimestre
                mes_inicio = (trimestre_num - 1) * 3 + 1
                primer_dia = date(año, mes_inicio, 1)
                mes_fin = mes_inicio + 2
                ultimo_dia = date(año, mes_fin, calendar.monthrange(año, mes_fin)[1])
                
                total = execute_query("""
                    SELECT COUNT(*) as total
                    FROM habitantes
                    WHERE Activo = 1
                    AND FechaRegistro BETWEEN %s AND %s
                """, (primer_dia, ultimo_dia), fetch_one=True)
                
                data.append({
                    'periodo': f"T{trimestre_num}-{año}",
                    'fecha_inicio': primer_dia.isoformat(),
                    'fecha_fin': ultimo_dia.isoformat(),
                    'total': total['total'] if total else 0,
                    'tipo': 'trimestre'
                })
        
        else:  # año por defecto
            # Últimos N años
            for i in range(cantidad_periodos - 1, -1, -1):
                año = hoy.year - i
                primer_dia = date(año, 1, 1)
                ultimo_dia = date(año, 12, 31)
                
                total = execute_query("""
                    SELECT COUNT(*) as total
                    FROM habitantes
                    WHERE Activo = 1
                    AND FechaRegistro BETWEEN %s AND %s
                """, (primer_dia, ultimo_dia), fetch_one=True)
                
                # Calcular crecimiento anual
                if i < cantidad_periodos - 1:
                    año_anterior = año - 1
                    primer_dia_anterior = date(año_anterior, 1, 1)
                    ultimo_dia_anterior = date(año_anterior, 12, 31)
                    
                    total_anterior = execute_query("""
                        SELECT COUNT(*) as total
                        FROM habitantes
                        WHERE Activo = 1
                        AND FechaRegistro BETWEEN %s AND %s
                    """, (primer_dia_anterior, ultimo_dia_anterior), fetch_one=True)
                    
                    crecimiento = calcular_variacion(
                        total['total'] if total else 0,
                        total_anterior['total'] if total_anterior else 0
                    )
                else:
                    crecimiento = 0
                    total_anterior = {'total': 0}
                
                data.append({
                    'periodo': str(año),
                    'fecha_inicio': primer_dia.isoformat(),
                    'fecha_fin': ultimo_dia.isoformat(),
                    'total': total['total'] if total else 0,
                    'total_anterior': total_anterior['total'] if total_anterior else 0,
                    'crecimiento': round(crecimiento, 2),
                    'tipo': 'año'
                })
        
        # Calcular tendencia
        if len(data) >= 2:
            primeros = data[0]['total']
            ultimos = data[-1]['total']
            if primeros > 0:
                tendencia = ((ultimos - primeros) / primeros) * 100
            else:
                tendencia = 0
        else:
            tendencia = 0
        
        return jsonify({
            'success': True,
            'tipo_rango': tipo_rango,
            'cantidad_periodos': cantidad_periodos,
            'tendencia_general': round(tendencia, 2),
            'crecimiento': data,
            'total_periodos': len(data)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener crecimiento temporal: {str(e)}'}), 500

@estadisticas_bp.route('/habitantes/distribucion-edades/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_distribucion_edades():
    """
    Distribución de habitantes por rangos de edad - Versión simplificada
    """
    try:
        tipo_rango = request.args.get('tipo_rango', 'mes')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        id_sector = request.args.get('id_sector', type=int)
        
        filtros = {
            'tipo_rango': tipo_rango,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        
        desde, hasta = obtener_rango_fechas(filtros)
        
        # ========== CONSTRUIR CONDICIONES ==========
        condiciones = ["h.Activo = 1", "h.FechaRegistro BETWEEN %s AND %s"]
        params = [desde, hasta]
        
        if id_sector:
            condiciones.append("h.IdSector = %s")
            params.append(id_sector)
        
        where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""
        
        # ========== RANGOS DE EDAD DETALLADOS (SIN PORCENTAJE EN LA MISMA CONSULTA) ==========
        query = f"""
            SELECT 
                CASE
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) < 1 THEN 'Menos de 1 año'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 1 AND 5 THEN '1-5 años'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 6 AND 12 THEN '6-12 años'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 13 AND 17 THEN '13-17 años'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 18 AND 24 THEN '18-24 años'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 25 AND 34 THEN '25-34 años'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 35 AND 44 THEN '35-44 años'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 45 AND 54 THEN '45-54 años'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 55 AND 64 THEN '55-64 años'
                    WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 65 AND 74 THEN '65-74 años'
                    ELSE '75+ años'
                END as rango_edad,
                COUNT(*) as cantidad,
                AVG(TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE())) as edad_promedio,
                MIN(TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE())) as edad_minima,
                MAX(TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE())) as edad_maxima
            FROM habitantes h
            {where_clause}
            GROUP BY rango_edad
            ORDER BY 
                CASE rango_edad
                    WHEN 'Menos de 1 año' THEN 1
                    WHEN '1-5 años' THEN 2
                    WHEN '6-12 años' THEN 3
                    WHEN '13-17 años' THEN 4
                    WHEN '18-24 años' THEN 5
                    WHEN '25-34 años' THEN 6
                    WHEN '35-44 años' THEN 7
                    WHEN '45-54 años' THEN 8
                    WHEN '55-64 años' THEN 9
                    WHEN '65-74 años' THEN 10
                    ELSE 11
                END
        """
        
        rangos_edades = execute_query(query, tuple(params))
        
        # ========== CALCULAR TOTAL PARA PORCENTAJES ==========
        total_query = f"SELECT COUNT(*) as total FROM habitantes h {where_clause}"
        total_result = execute_query(total_query, tuple(params), fetch_one=True)
        total = total_result['total'] if total_result else 0
        
        # Agregar porcentajes a los resultados
        for rango in rangos_edades:
            if total > 0:
                rango['porcentaje'] = round((rango['cantidad'] / total) * 100, 2)
            else:
                rango['porcentaje'] = 0
        
        # ========== RESUMEN POR CATEGORÍA AMPLIA ==========
        resumen_query = f"""
            SELECT 
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) < 18 THEN 1 ELSE 0 END) as menores,
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 18 AND 29 THEN 1 ELSE 0 END) as jovenes,
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 30 AND 44 THEN 1 ELSE 0 END) as adultos_jovenes,
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 45 AND 59 THEN 1 ELSE 0 END) as adultos,
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) BETWEEN 60 AND 74 THEN 1 ELSE 0 END) as adultos_mayores,
                SUM(CASE WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) >= 75 THEN 1 ELSE 0 END) as tercera_edad
            FROM habitantes h
            {where_clause}
        """
        
        resumen_categorias = execute_query(resumen_query, tuple(params), fetch_one=True)
        
        # ========== ESTADÍSTICAS GENERALES ==========
        estadisticas_query = f"""
            SELECT 
                AVG(TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE())) as edad_promedio_general,
                MIN(TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE())) as edad_minima_general,
                MAX(TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE())) as edad_maxima_general
            FROM habitantes h
            {where_clause}
        """
        
        estadisticas_generales = execute_query(estadisticas_query, tuple(params), fetch_one=True)
        
        return jsonify({
            'success': True,
            'filtros': {
                'id_sector': id_sector,
                'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()}
            },
            'rangos_detallados': rangos_edades,
            'total_general': total,
            'resumen_categorias': {
                'menores': resumen_categorias['menores'] if resumen_categorias else 0,
                'jovenes': resumen_categorias['jovenes'] if resumen_categorias else 0,
                'adultos_jovenes': resumen_categorias['adultos_jovenes'] if resumen_categorias else 0,
                'adultos': resumen_categorias['adultos'] if resumen_categorias else 0,
                'adultos_mayores': resumen_categorias['adultos_mayores'] if resumen_categorias else 0,
                'tercera_edad': resumen_categorias['tercera_edad'] if resumen_categorias else 0
            },
            'estadisticas_generales': {
                'edad_promedio': round(estadisticas_generales['edad_promedio_general'], 1) if estadisticas_generales else 0,
                'edad_minima': estadisticas_generales['edad_minima_general'] if estadisticas_generales else 0,
                'edad_maxima': estadisticas_generales['edad_maxima_general'] if estadisticas_generales else 0,
                'total': total
            }
        }), 200
        
    except Exception as e:
        print(f"Error en get_distribucion_edades: {str(e)}")
        return jsonify({'success': False, 'message': f'Error al obtener distribución de edades: {str(e)}'}), 500

# ====================================================
# NUEVOS ENDPOINTS PARA SACRAMENTOS PENDIENTES
# ====================================================

@estadisticas_bp.route('/habitantes/sacramentos-pendientes/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_sacramentos_pendientes():
    """
    Retorna cantidad de habitantes que NO tienen cada sacramento
    Ejemplo: Bautismo: 320, Comunión: 210, etc.
    """
    try:
        # Obtener filtros básicos
        id_sector = request.args.get('id_sector', type=int)
        id_sacramento = request.args.get('id_sacramento', type=int)  # Para filtrar solo uno
        
        # Construir condiciones base
        condiciones_habitantes = ["h.Activo = 1"]
        params = []
        
        if id_sector:
            condiciones_habitantes.append("h.IdSector = %s")
            params.append(id_sector)
        
        where_habitantes = "WHERE " + " AND ".join(condiciones_habitantes) if condiciones_habitantes else ""
        
        # 1. Total de habitantes activos (según filtros)
        total_query = f"SELECT COUNT(*) as total FROM habitantes h {where_habitantes}"
        total_result = execute_query(total_query, tuple(params) if params else None, fetch_one=True)
        total_habitantes = total_result['total'] if total_result else 0
        
        # 2. Sacramentos pendientes por tipo
        if id_sacramento:
            # Solo un sacramento específico
            sacramentos_query = """
                SELECT 
                    ts.IdSacramento as id,
                    ts.Descripcion as nombre,
                    COUNT(*) as cantidad
                FROM tiposacramentos ts
                CROSS JOIN habitantes h
                WHERE h.Activo = 1
                AND ts.IdSacramento = %s
                AND NOT EXISTS (
                    SELECT 1 FROM habitante_sacramento hs
                    WHERE hs.IdSacramento = ts.IdSacramento
                    AND hs.IdHabitante = h.IdHabitante
                )
                GROUP BY ts.IdSacramento, ts.Descripcion
            """
            sacramentos_params = [id_sacramento] + params
            sacramentos_pendientes = execute_query(sacramentos_query, tuple(sacramentos_params))
        else:
            # Todos los sacramentos
            sacramentos_query = f"""
                SELECT 
                    ts.IdSacramento as id,
                    ts.Descripcion as nombre,
                    COUNT(*) as cantidad
                FROM tiposacramentos ts
                CROSS JOIN habitantes h
                {where_habitantes}
                AND NOT EXISTS (
                    SELECT 1 FROM habitante_sacramento hs
                    WHERE hs.IdSacramento = ts.IdSacramento
                    AND hs.IdHabitante = h.IdHabitante
                )
                GROUP BY ts.IdSacramento, ts.Descripcion
                ORDER BY cantidad DESC
            """
            sacramentos_pendientes = execute_query(sacramentos_query, tuple(params) if params else None)
        
        # Calcular porcentajes
        for sacramento in sacramentos_pendientes:
            if total_habitantes > 0:
                sacramento['porcentaje'] = round((sacramento['cantidad'] / total_habitantes) * 100, 1)
            else:
                sacramento['porcentaje'] = 0
        
        return jsonify({
            'success': True,
            'total_habitantes': total_habitantes,
            'sacramentos_pendientes': sacramentos_pendientes,
            'filtros': {
                'id_sector': id_sector,
                'id_sacramento': id_sacramento
            }
        }), 200
        
    except Exception as e:
        print(f"Error en get_sacramentos_pendientes: {str(e)}")
        return jsonify({'success': False, 'message': f'Error al obtener sacramentos pendientes: {str(e)}'}), 500


@estadisticas_bp.route('/habitantes/lista-sin-sacramento/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_lista_sin_sacramento():
    """
    Retorna lista de personas que NO tienen un sacramento específico
    Incluye datos de contacto para visitas
    """
    try:
        id_sacramento = request.args.get('id_sacramento', type=int)
        id_sector = request.args.get('id_sector', type=int)
        
        if not id_sacramento:
            return jsonify({'success': False, 'message': 'Se requiere id_sacramento'}), 400
        
        # Construir condiciones
        condiciones = ["h.Activo = 1"]
        params = [id_sacramento]
        
        if id_sector:
            condiciones.append("h.IdSector = %s")
            params.append(id_sector)
        
        condiciones.append("""
            NOT EXISTS (
                SELECT 1 FROM habitante_sacramento hs
                WHERE hs.IdHabitante = h.IdHabitante
                AND hs.IdSacramento = %s
            )
        """)
        
        where_clause = "WHERE " + " AND ".join(condiciones)
        
        query = f"""
            SELECT 
                h.IdHabitante,
                CONCAT(h.Nombre, ' ', h.Apellido) as nombre_completo,
                td.Descripcion as tipo_documento,
                h.NumeroDocumento,
                TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) as edad,
                s.Descripcion as sector,
                h.Direccion,
                h.Telefono,
                h.CorreoElectronico,
                h.FechaRegistro,
                GROUP_CONCAT(DISTINCT ts2.Descripcion SEPARATOR ', ') as otros_sacramentos,
                COUNT(DISTINCT hs2.IdSacramento) as total_sacramentos_actuales
            FROM habitantes h
            LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
            LEFT JOIN sector s ON h.IdSector = s.IdSector
            LEFT JOIN habitante_sacramento hs2 ON h.IdHabitante = hs2.IdHabitante
            LEFT JOIN tiposacramentos ts2 ON hs2.IdSacramento = ts2.IdSacramento
            {where_clause}
            GROUP BY h.IdHabitante, h.Nombre, h.Apellido, td.Descripcion, h.NumeroDocumento,
                     h.FechaNacimiento, s.Descripcion, h.Direccion, h.Telefono, 
                     h.CorreoElectronico, h.FechaRegistro
            ORDER BY h.Apellido, h.Nombre
            LIMIT 1000
        """
        
        personas = execute_query(query, tuple(params))
        
        # Obtener nombre del sacramento
        sacramento_query = "SELECT Descripcion FROM tiposacramentos WHERE IdSacramento = %s"
        sacramento_info = execute_query(sacramento_query, (id_sacramento,), fetch_one=True)
        nombre_sacramento = sacramento_info['Descripcion'] if sacramento_info else f"Sacramento {id_sacramento}"
        
        return jsonify({
            'success': True,
            'sacramento': {
                'id': id_sacramento,
                'nombre': nombre_sacramento
            },
            'total_personas': len(personas),
            'personas': personas,
            'filtros': {
                'id_sector': id_sector
            }
        }), 200
        
    except Exception as e:
        print(f"Error en get_lista_sin_sacramento: {str(e)}")
        return jsonify({'success': False, 'message': f'Error al obtener lista: {str(e)}'}), 500


@estadisticas_bp.route('/habitantes/sectores-criticos/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_sectores_criticos():
    """
    Identifica sectores con baja cobertura sacramental
    """
    try:
        id_sacramento = request.args.get('id_sacramento', type=int)
        umbral_porcentaje = request.args.get('umbral', default=30, type=float)
        
        if not id_sacramento:
            return jsonify({'success': False, 'message': 'Se requiere id_sacramento'}), 400
        
        query = """
            SELECT 
                s.IdSector,
                s.Descripcion as sector,
                COUNT(h.IdHabitante) as total_habitantes,
                COUNT(DISTINCT CASE 
                    WHEN hs.IdSacramento = %s THEN h.IdHabitante 
                END) as con_sacramento,
                COUNT(DISTINCT CASE 
                    WHEN hs.IdSacramento IS NULL OR hs.IdSacramento != %s THEN h.IdHabitante 
                END) as sin_sacramento,
                CASE 
                    WHEN COUNT(h.IdHabitante) > 0 THEN 
                        ROUND((COUNT(DISTINCT CASE 
                            WHEN hs.IdSacramento = %s THEN h.IdHabitante 
                        END) * 100.0 / COUNT(h.IdHabitante)), 2)
                    ELSE 0 
                END as porcentaje_cobertura
            FROM sector s
            LEFT JOIN habitantes h ON s.IdSector = h.IdSector AND h.Activo = 1
            LEFT JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante AND hs.IdSacramento = %s
            WHERE s.Activo = 1
            GROUP BY s.IdSector, s.Descripcion
            HAVING porcentaje_cobertura < %s OR porcentaje_cobertura IS NULL
            ORDER BY porcentaje_cobertura ASC
        """
        
        sectores = execute_query(query, (id_sacramento, id_sacramento, id_sacramento, id_sacramento, umbral_porcentaje))
        
        # Obtener nombre del sacramento
        sacramento_query = "SELECT Descripcion FROM tiposacramentos WHERE IdSacramento = %s"
        sacramento_info = execute_query(sacramento_query, (id_sacramento,), fetch_one=True)
        nombre_sacramento = sacramento_info['Descripcion'] if sacramento_info else f"Sacramento {id_sacramento}"
        
        return jsonify({
            'success': True,
            'sacramento': {
                'id': id_sacramento,
                'nombre': nombre_sacramento,
                'umbral_porcentaje': umbral_porcentaje
            },
            'total_sectores_criticos': len(sectores),
            'sectores': sectores
        }), 200
        
    except Exception as e:
        print(f"Error en get_sectores_criticos: {str(e)}")
        return jsonify({'success': False, 'message': f'Error al obtener sectores críticos: {str(e)}'}), 500


@estadisticas_bp.route('/habitantes/resumen-sacramento/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_resumen_sacramento():
    """
    Resumen específico para un sacramento: total, sector con más/menos, etc.
    """
    try:
        id_sacramento = request.args.get('id_sacramento', type=int)
        
        if not id_sacramento:
            return jsonify({'success': False, 'message': 'Se requiere id_sacramento'}), 400
        
        # 1. Totales generales
        totales_query = """
            SELECT 
                COUNT(DISTINCT h.IdHabitante) as total_con_sacramento,
                (SELECT COUNT(*) FROM habitantes WHERE Activo = 1) as total_habitantes
            FROM habitantes h
            INNER JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
            WHERE h.Activo = 1
            AND hs.IdSacramento = %s
        """
        totales = execute_query(totales_query, (id_sacramento,), fetch_one=True)
        
        total_con = totales['total_con_sacramento'] if totales else 0
        total_habitantes = totales['total_habitantes'] if totales else 0
        total_sin = total_habitantes - total_con if total_habitantes else 0
        porcentaje_con = round((total_con / total_habitantes * 100), 2) if total_habitantes > 0 else 0
        
        # 2. Sector con MÁS sacramentos
        sector_mas_query = """
            SELECT 
                s.IdSector,
                s.Descripcion as sector,
                COUNT(DISTINCT h.IdHabitante) as cantidad,
                ROUND((COUNT(DISTINCT h.IdHabitante) * 100.0 / (
                    SELECT COUNT(*) FROM habitantes h2 
                    WHERE h2.Activo = 1 AND h2.IdSector = s.IdSector
                )), 2) as porcentaje_sector
            FROM sector s
            INNER JOIN habitantes h ON s.IdSector = h.IdSector AND h.Activo = 1
            INNER JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante AND hs.IdSacramento = %s
            WHERE s.Activo = 1
            GROUP BY s.IdSector, s.Descripcion
            ORDER BY cantidad DESC
            LIMIT 1
        """
        sector_mas = execute_query(sector_mas_query, (id_sacramento,), fetch_one=True)
        
        # 3. Sector con MENOS sacramentos (excluyendo cero)
        sector_menos_query = """
            SELECT 
                s.IdSector,
                s.Descripcion as sector,
                COUNT(DISTINCT h.IdHabitante) as cantidad,
                ROUND((COUNT(DISTINCT h.IdHabitante) * 100.0 / (
                    SELECT COUNT(*) FROM habitantes h2 
                    WHERE h2.Activo = 1 AND h2.IdSector = s.IdSector
                )), 2) as porcentaje_sector
            FROM sector s
            LEFT JOIN habitantes h ON s.IdSector = h.IdSector AND h.Activo = 1
            LEFT JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante AND hs.IdSacramento = %s
            WHERE s.Activo = 1
            AND EXISTS (SELECT 1 FROM habitantes h3 WHERE h3.IdSector = s.IdSector AND h3.Activo = 1)
            GROUP BY s.IdSector, s.Descripcion
            HAVING COUNT(DISTINCT h.IdHabitante) > 0
            ORDER BY cantidad ASC
            LIMIT 1
        """
        sector_menos = execute_query(sector_menos_query, (id_sacramento,), fetch_one=True)
        
        # 4. Sector con CERO sacramentos
        sector_cero_query = """
            SELECT 
                s.IdSector,
                s.Descripcion as sector,
                0 as cantidad,
                0 as porcentaje_sector
            FROM sector s
            WHERE s.Activo = 1
            AND NOT EXISTS (
                SELECT 1 FROM habitantes h
                INNER JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
                WHERE h.IdSector = s.IdSector
                AND h.Activo = 1
                AND hs.IdSacramento = %s
            )
            AND EXISTS (SELECT 1 FROM habitantes h2 WHERE h2.IdSector = s.IdSector AND h2.Activo = 1)
            ORDER BY s.Descripcion
        """
        sectores_cero = execute_query(sector_cero_query, (id_sacramento,))
        
        # 5. Obtener nombre del sacramento
        sacramento_query = "SELECT Descripcion FROM tiposacramentos WHERE IdSacramento = %s"
        sacramento_info = execute_query(sacramento_query, (id_sacramento,), fetch_one=True)
        nombre_sacramento = sacramento_info['Descripcion'] if sacramento_info else f"Sacramento {id_sacramento}"
        
        return jsonify({
            'success': True,
            'sacramento': {
                'id': id_sacramento,
                'nombre': nombre_sacramento
            },
            'totales': {
                'con_sacramento': total_con,
                'sin_sacramento': total_sin,
                'total_habitantes': total_habitantes,
                'porcentaje_con': porcentaje_con,
                'porcentaje_sin': 100 - porcentaje_con if porcentaje_con else 100
            },
            'sectores_destacados': {
                'con_mas': sector_mas,
                'con_menos': sector_menos,
                'con_cero': sectores_cero,
                'total_sectores_cero': len(sectores_cero)
            }
        }), 200
        
    except Exception as e:
        print(f"Error en get_resumen_sacramento: {str(e)}")
        return jsonify({'success': False, 'message': f'Error al obtener resumen sacramental: {str(e)}'}), 500

@estadisticas_bp.route('/habitantes/reporte-completo/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_reporte_completo():
    """
    Reporte completo de habitantes con todos los filtros posibles
    """
    try:
        tipo_rango = request.args.get('tipo_rango', 'mes')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        # Filtros adicionales
        id_sector = request.args.get('id_sector', type=int)
        id_sacramento = request.args.get('id_sacramento', type=int)
        edad_min = request.args.get('edad_min', type=int)
        edad_max = request.args.get('edad_max', type=int)
        con_sacramento = request.args.get('con_sacramento')  # 'si', 'no'
        id_estado_civil = request.args.get('id_estado_civil', type=int)
        id_sexo = request.args.get('id_sexo', type=int)
        id_religion = request.args.get('id_religion', type=int)
        
        filtros = {
            'tipo_rango': tipo_rango,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        
        desde, hasta = obtener_rango_fechas(filtros)
        
        # ========== CONSTRUIR CONSULTA DINÁMICA ==========
        condiciones = ["h.Activo = 1", "h.FechaRegistro BETWEEN %s AND %s"]
        params = [desde, hasta]
        
        if id_sector:
            condiciones.append("h.IdSector = %s")
            params.append(id_sector)
        
        if id_sacramento:
            condiciones.append("EXISTS (SELECT 1 FROM habitante_sacramento hs WHERE hs.IdHabitante = h.IdHabitante AND hs.IdSacramento = %s)")
            params.append(id_sacramento)
        
        if con_sacramento == 'si':
            condiciones.append("EXISTS (SELECT 1 FROM habitante_sacramento hs WHERE hs.IdHabitante = h.IdHabitante)")
        elif con_sacramento == 'no':
            condiciones.append("NOT EXISTS (SELECT 1 FROM habitante_sacramento hs WHERE hs.IdHabitante = h.IdHabitante)")
        
        if edad_min is not None:
            fecha_max_nacimiento = date.today() - timedelta(days=edad_min*365)
            condiciones.append("h.FechaNacimiento <= %s")
            params.append(fecha_max_nacimiento)
        
        if edad_max is not None:
            fecha_min_nacimiento = date.today() - timedelta(days=edad_max*365)
            condiciones.append("h.FechaNacimiento >= %s")
            params.append(fecha_min_nacimiento)
        
        if id_estado_civil:
            condiciones.append("h.IdEstadoCivil = %s")
            params.append(id_estado_civil)
        
        if id_sexo:
            condiciones.append("h.IdSexo = %s")
            params.append(id_sexo)
        
        if id_religion:
            condiciones.append("h.IdReligion = %s")
            params.append(id_religion)
        
        where_clause = "WHERE " + " AND ".join(condiciones)
        
        # ========== CONSULTA PRINCIPAL ==========
        query = f"""
            SELECT 
                h.IdHabitante,
                CONCAT(h.Nombre, ' ', h.Apellido) as nombre_completo,
                td.Descripcion as tipo_documento,
                h.NumeroDocumento,
                h.FechaNacimiento,
                TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) as edad,
                s.Descripcion as sector,
                COALESCE(gf.Descripcion, 'Sin grupo') as grupo_familiar,
                ec.Nombre as estado_civil,
                sex.Nombre as sexo,
                r.Nombre as religion,
                tp.Nombre as tipo_poblacion,
                GROUP_CONCAT(DISTINCT ts.Descripcion ORDER BY ts.Descripcion SEPARATOR ', ') as sacramentos,
                COUNT(DISTINCT hs.IdSacramento) as total_sacramentos,
                h.Telefono,
                h.CorreoElectronico,
                h.Direccion,
                h.Hijos,
                h.DiscapacidadParaAsistir,
                CASE WHEN h.TieneImpedimentoSalud = 1 THEN 'Sí' ELSE 'No' END as tiene_impedimento,
                h.MotivoImpedimentoSalud,
                h.FechaRegistro,
                DATE_FORMAT(h.FechaRegistro, '%%d/%%m/%%Y') as fecha_registro_formateada
            FROM habitantes h
            LEFT JOIN tipodocumento td ON h.IdTipoDocumento = td.IdTipoDocumento
            LEFT JOIN sector s ON h.IdSector = s.IdSector
            LEFT JOIN grupofamiliar gf ON h.IdGrupoFamiliar = gf.IdGrupoFamiliar
            LEFT JOIN estados_civiles ec ON h.IdEstadoCivil = ec.IdEstadoCivil
            LEFT JOIN sexos sex ON h.IdSexo = sex.IdSexo
            LEFT JOIN religiones r ON h.IdReligion = r.IdReligion
            LEFT JOIN tipopoblacion tp ON h.IdTipoPoblacion = tp.IdTipoPoblacion
            LEFT JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
            LEFT JOIN tiposacramentos ts ON hs.IdSacramento = ts.IdSacramento
            {where_clause}
            GROUP BY h.IdHabitante, h.Nombre, h.Apellido, td.Descripcion, h.NumeroDocumento, 
                     h.FechaNacimiento, s.Descripcion, gf.Descripcion, ec.Nombre, sex.Nombre, 
                     r.Nombre, tp.Nombre, h.Telefono, h.CorreoElectronico, h.Direccion, 
                     h.Hijos, h.DiscapacidadParaAsistir, h.TieneImpedimentoSalud, 
                     h.MotivoImpedimentoSalud, h.FechaRegistro
            ORDER BY h.Apellido, h.Nombre, h.FechaRegistro DESC
            LIMIT 1000
        """
        
        habitantes = execute_query(query, tuple(params))
        
        # ========== RESUMEN DEL REPORTE ==========
        total_registros = len(habitantes)
        
        if total_registros > 0:
            # Estadísticas del reporte
            edad_promedio = round(sum(h['edad'] for h in habitantes) / total_registros, 1)
            con_sacramento_count = sum(1 for h in habitantes if h['total_sacramentos'] > 0)
            sin_sacramento_count = total_registros - con_sacramento_count
            con_impedimento_count = sum(1 for h in habitantes if h['tiene_impedimento'] == 'Sí')
            
            resumen = {
                'total_registros': total_registros,
                'edad_promedio': edad_promedio,
                'con_sacramento': con_sacramento_count,
                'sin_sacramento': sin_sacramento_count,
                'con_impedimento': con_impedimento_count,
                'hijos_promedio': round(sum(h['Hijos'] for h in habitantes) / total_registros, 1)
            }
        else:
            resumen = {
                'total_registros': 0,
                'edad_promedio': 0,
                'con_sacramento': 0,
                'sin_sacramento': 0,
                'con_impedimento': 0,
                'hijos_promedio': 0
            }
        
        return jsonify({
            'success': True,
            'filtros_aplicados': {
                'tipo_rango': tipo_rango,
                'desde': desde.isoformat(),
                'hasta': hasta.isoformat(),
                'id_sector': id_sector,
                'id_sacramento': id_sacramento,
                'edad_min': edad_min,
                'edad_max': edad_max,
                'con_sacramento': con_sacramento,
                'id_estado_civil': id_estado_civil,
                'id_sexo': id_sexo,
                'id_religion': id_religion
            },
            'resumen': resumen,
            'habitantes': habitantes
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener reporte completo: {str(e)}'}), 500

@estadisticas_bp.route('/habitantes/opciones-filtros/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_opciones_filtros():
    """
    Obtiene todas las opciones para los filtros
    """
    try:
        # Sectores
        sectores = execute_query("""
            SELECT IdSector as id, Descripcion as nombre
            FROM sector
            WHERE Activo = 1
            ORDER BY Descripcion
        """)
        
        # Sacramentos
        sacramentos = execute_query("""
            SELECT IdSacramento as id, Descripcion as nombre, Costo
            FROM tiposacramentos
            ORDER BY Descripcion
        """)
        
        # Estados civiles
        estados_civiles = execute_query("""
            SELECT IdEstadoCivil as id, Nombre as nombre
            FROM estados_civiles
            ORDER BY Nombre
        """)
        
        # Sexos
        sexos = execute_query("""
            SELECT IdSexo as id, Nombre as nombre
            FROM sexos
            ORDER BY Nombre
        """)
        
        # Religiones
        religiones = execute_query("""
            SELECT IdReligion as id, Nombre as nombre
            FROM religiones
            ORDER BY Nombre
        """)
        
        # Tipos de población
        tipos_poblacion = execute_query("""
            SELECT IdTipoPoblacion as id, Nombre as nombre, Descripcion
            FROM tipopoblacion
            ORDER BY Nombre
        """)
        
        # Rangos de tiempo predefinidos
        rangos_tiempo = [
            {'id': 'semana', 'nombre': 'Última semana'},
            {'id': '15dias', 'nombre': 'Últimos 15 días'},
            {'id': '30dias', 'nombre': 'Últimos 30 días'},
            {'id': 'mes', 'nombre': 'Mes actual'},
            {'id': 'trimestre', 'nombre': 'Trimestre actual'},
            {'id': 'semestre', 'nombre': 'Semestre actual'},
            {'id': 'anio', 'nombre': 'Año actual'},
            {'id': 'personalizado', 'nombre': 'Personalizado'}
        ]
        
        # Rangos de edad predefinidos
        rangos_edad = [
            {'id': 'menores', 'nombre': 'Menores (0-17)', 'min': 0, 'max': 17},
            {'id': 'jovenes', 'nombre': 'Jóvenes (18-29)', 'min': 18, 'max': 29},
            {'id': 'adultos', 'nombre': 'Adultos (30-59)', 'min': 30, 'max': 59},
            {'id': 'mayores', 'nombre': 'Adultos Mayores (60+)', 'min': 60, 'max': 120}
        ]
        
        return jsonify({
            'success': True,
            'opciones': {
                'sectores': sectores,
                'sacramentos': sacramentos,
                'estados_civiles': estados_civiles,
                'sexos': sexos,
                'religiones': religiones,
                'tipos_poblacion': tipos_poblacion,
                'rangos_tiempo': rangos_tiempo,
                'rangos_edad': rangos_edad
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener opciones: {str(e)}'}), 500

@estadisticas_bp.route('/habitantes/resumen-ejecutivo/', methods=['GET'])
@jwt_required()
@require_rol('Administrador')
def get_resumen_ejecutivo():
    """
    Resumen ejecutivo para dashboard
    """
    try:
        hoy = datetime.now()
        inicio_mes = hoy.replace(day=1)
        fin_mes = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])
        
        inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
        fin_mes_anterior = inicio_mes - timedelta(days=1)
        
        # ========== TOTAL HABITANTES ==========
        total_actual = execute_query("""
            SELECT COUNT(*) as total
            FROM habitantes
            WHERE Activo = 1
            AND FechaRegistro BETWEEN %s AND %s
        """, (inicio_mes, fin_mes), fetch_one=True)
        
        total_anterior = execute_query("""
            SELECT COUNT(*) as total
            FROM habitantes
            WHERE Activo = 1
            AND FechaRegistro BETWEEN %s AND %s
        """, (inicio_mes_anterior, fin_mes_anterior), fetch_one=True)
        
        crecimiento = calcular_variacion(
            total_actual['total'] if total_actual else 0,
            total_anterior['total'] if total_anterior else 0
        )
        
        # ========== SECTORES CON MÁS CRECIMIENTO ==========
        sectores_crecimiento = execute_query("""
            SELECT 
                s.Descripcion as sector,
                COUNT(h.IdHabitante) as cantidad,
                COUNT(DISTINCT h.IdGrupoFamiliar) as familias,
                ROUND(AVG(TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE())), 1) as edad_promedio
            FROM habitantes h
            INNER JOIN sector s ON h.IdSector = s.IdSector
            WHERE h.Activo = 1
            AND h.FechaRegistro BETWEEN %s AND %s
            GROUP BY s.IdSector, s.Descripcion
            ORDER BY cantidad DESC
            LIMIT 5
        """, (inicio_mes, fin_mes))
        
        # ========== SACRAMENTOS DEL MES ==========
        sacramentos_mes = execute_query("""
            SELECT 
                ts.Descripcion as sacramento,
                COUNT(*) as total,
                COUNT(DISTINCT h.IdSector) as sectores
            FROM habitante_sacramento hs
            INNER JOIN tiposacramentos ts ON hs.IdSacramento = ts.IdSacramento
            INNER JOIN habitantes h ON hs.IdHabitante = h.IdHabitante
            WHERE h.Activo = 1
            AND YEAR(hs.FechaSacramento) = YEAR(CURDATE())
            AND MONTH(hs.FechaSacramento) = MONTH(CURDATE())
            GROUP BY ts.IdSacramento, ts.Descripcion
            ORDER BY total DESC
            LIMIT 5
        """)
        
        # ========== ESTADÍSTICAS RÁPIDAS ==========
        estadisticas_rapidas = execute_query("""
            SELECT 
                COUNT(DISTINCT h.IdHabitante) as total_habitantes,
                COUNT(DISTINCT h.IdGrupoFamiliar) as total_familias,
                COUNT(DISTINCT CASE WHEN TIMESTAMPDIFF(YEAR, h.FechaNacimiento, CURDATE()) < 18 THEN h.IdHabitante END) as menores,
                COUNT(DISTINCT CASE WHEN h.TieneImpedimentoSalud = 1 THEN h.IdHabitante END) as con_impedimento,
                COUNT(DISTINCT hs.IdHabitante) as con_sacramento,
                COUNT(DISTINCT h.IdSector) as sectores_activos
            FROM habitantes h
            LEFT JOIN habitante_sacramento hs ON h.IdHabitante = hs.IdHabitante
            WHERE h.Activo = 1
            AND h.FechaRegistro BETWEEN %s AND %s
        """, (inicio_mes, fin_mes), fetch_one=True)
        
        return jsonify({
            'success': True,
            'periodo': {
                'actual': {'desde': inicio_mes.isoformat(), 'hasta': fin_mes.isoformat()},
                'anterior': {'desde': inicio_mes_anterior.isoformat(), 'hasta': fin_mes_anterior.isoformat()}
            },
            'resumen': {
                'total_habitantes': total_actual['total'] if total_actual else 0,
                'total_habitantes_anterior': total_anterior['total'] if total_anterior else 0,
                'crecimiento': round(crecimiento, 2),
                'estadisticas_rapidas': estadisticas_rapidas
            },
            'destacados': {
                'sectores_crecimiento': sectores_crecimiento,
                'sacramentos_mes': sacramentos_mes
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al obtener resumen ejecutivo: {str(e)}'}), 500




# ==========================================
# HELPERS COMUNES
# ==========================================

def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _get_date_range():
    """
    Maneja filtros de fecha:
    - rango = dia | semana | mes | anio
    - desde, hasta = YYYY-MM-DD
    """
    rango = (request.args.get("rango") or "").lower()
    desde_str = request.args.get("desde")
    hasta_str = request.args.get("hasta")
    today = date.today()

    if desde_str and hasta_str:
        return (_parse_date(desde_str), _parse_date(hasta_str))

    if rango == "dia":
        return (today, today)

    if rango == "semana":
        start = today - timedelta(days=today.weekday())   # lunes
        end = start + timedelta(days=6)                   # domingo
        return (start, end)

    if rango == "mes":
        start = today.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        end = next_month - timedelta(days=1)
        return (start, end)

    if rango == "anio":
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
        return (start, end)

    return (None, None)


def _add_date_filter(filters, params, column_name: str):
    """
    Aplica el rango de fechas actual a una columna específica.
    """
    desde, hasta = _get_date_range()
    if desde:
        filters.append(f"{column_name} >= %s")
        params.append(desde.isoformat())
    if hasta:
        filters.append(f"{column_name} <= %s")
        params.append(hasta.isoformat())


# ==========================================
# 1) DASHBOARD GLOBAL
#    GET /api/estadisticas/resumen/
# ==========================================

@estadisticas_bp.route("/resumen/", methods=["GET"])
@jwt_required()
@require_rol("Administrador")
def resumen_global():
    """
    Dashboard principal del módulo de estadísticas.

    Devuelve:
    - habitantes: totales, familias, sacramentos, sectores, enfermos
    - citas: próximas, estados, semana con más/menos, padre con más/menos
    - grupos: total grupos, tareas por estado, grupos con más/menos tareas, más/menos integrantes
    - finanzas: mayor ingreso/egreso, totales ingresos/egresos, serie mensual
    """
    try:
        # ======================
        # HÁBITANTES
        # ======================
        filtros_h = ["h.Activo = 1"]
        params_h = []
        _add_date_filter(filtros_h, params_h, "DATE(h.FechaRegistro)")
        where_h = "WHERE " + " AND ".join(filtros_h) if filtros_h else ""

        row_total_h = execute_query(
            f"SELECT COUNT(*) AS total FROM habitantes h {where_h};",
            tuple(params_h) if params_h else None,
            fetch_one=True
        )
        total_habitantes = row_total_h["total"] if row_total_h else 0

        row_total_f = execute_query(
            "SELECT COUNT(*) AS total FROM grupofamiliar gf WHERE gf.Activo = 1;",
            fetch_one=True
        )
        total_familias = row_total_f["total"] if row_total_f else 0

        total_con_sac = 0
        if total_habitantes:
            row_con = execute_query(
                f"""
                SELECT COUNT(DISTINCT h.IdHabitante) AS total_con
                FROM habitantes h
                JOIN habitante_sacramento hs ON hs.IdHabitante = h.IdHabitante
                {where_h}
                """,
                tuple(params_h) if params_h else None,
                fetch_one=True
            )
            total_con_sac = row_con["total_con"] if row_con else 0

        total_sin_sac = total_habitantes - total_con_sac if total_habitantes else 0

        sectores = execute_query(
            f"""
            SELECT 
              s.IdSector,
              s.Descripcion,
              COUNT(*) AS total
            FROM sector s
            JOIN habitantes h ON h.IdSector = s.IdSector
            {where_h}
            GROUP BY s.IdSector, s.Descripcion
            ORDER BY total DESC
            """,
            tuple(params_h) if params_h else None
        )
        sector_mas = sectores[0] if sectores else None
        sector_menos = sectores[-1] if sectores else None

        filtros_enf = filtros_h + ["h.TieneImpedimentoSalud = 1"]
        where_enf = "WHERE " + " AND ".join(filtros_enf)
        sectores_enfermos = execute_query(
            f"""
            SELECT 
              s.IdSector,
              s.Descripcion,
              COUNT(*) AS total_enfermos
            FROM sector s
            JOIN habitantes h ON h.IdSector = s.IdSector
            {where_enf}
            GROUP BY s.IdSector, s.Descripcion
            ORDER BY total_enfermos DESC
            """,
            tuple(params_h) if params_h else None
        )

        # ======================
        # CITAS
        # ======================
        filtros_c = ["ac.Activo = 1"]
        params_c = []
        _add_date_filter(filtros_c, params_c, "ac.Fecha")

        estado_cita = request.args.get("estado_cita")
        padre = request.args.get("padre")
        tipo_cita = request.args.get("tipo_cita")

        if estado_cita and estado_cita.isdigit():
            filtros_c.append("ac.IdEstadoCita = %s")
            params_c.append(int(estado_cita))
        if padre and padre.isdigit():
            filtros_c.append("ac.IdPadre = %s")
            params_c.append(int(padre))
        if tipo_cita and tipo_cita.isdigit():
            filtros_c.append("ac.IdTipoCita = %s")
            params_c.append(int(tipo_cita))

        where_c = "WHERE " + " AND ".join(filtros_c) if filtros_c else ""

        proximas = execute_query(
            f"""
            SELECT 
              ac.IdAsignacionCita,
              ac.NombreSolicitante,
              ac.CelularSolicitante,
              ac.Fecha,
              TIME_FORMAT(ac.Hora, '%%H:%%i') AS Hora,
              ac.IdPadre,
              CONCAT(p.Nombre, ' ', p.Apellido) AS PadreNombre,
              ac.IdEstadoCita,
              ec.Descripcion AS EstadoDescripcion,
              ac.IdTipoCita,
              tc.Descripcion AS TipoDescripcion
            FROM asignacioncita ac
            LEFT JOIN padre p       ON p.IdPadre       = ac.IdPadre
            LEFT JOIN estadocita ec ON ec.IdEstadoCita = ac.IdEstadoCita
            LEFT JOIN tipocita tc   ON tc.IdTipoCita   = ac.IdTipoCita
            {where_c} AND ac.Fecha >= CURDATE()
            ORDER BY ac.Fecha ASC, ac.Hora ASC
            LIMIT 5
            """,
            tuple(params_c) if params_c else None
        )

        estados_citas = execute_query(
            f"""
            SELECT 
              ec.Descripcion AS Estado,
              COUNT(*) AS total
            FROM asignacioncita ac
            JOIN estadocita ec ON ec.IdEstadoCita = ac.IdEstadoCita
            {where_c}
            GROUP BY ec.Descripcion
            """,
            tuple(params_c) if params_c else None
        )

        semanas = execute_query(
            f"""
            SELECT 
              YEARWEEK(ac.Fecha, 1) AS semana,
              MIN(ac.Fecha) AS fecha_inicio,
              MAX(ac.Fecha) AS fecha_fin,
              COUNT(*) AS total
            FROM asignacioncita ac
            {where_c}
            GROUP BY YEARWEEK(ac.Fecha, 1)
            ORDER BY total DESC
            """,
            tuple(params_c) if params_c else None
        )
        semana_mas = semanas[0] if semanas else None
        semana_menos = semanas[-1] if semanas else None

        padres_citas = execute_query(
            f"""
            SELECT 
              p.IdPadre,
              CONCAT(p.Nombre, ' ', p.Apellido) AS Padre,
              COUNT(*) AS total
            FROM asignacioncita ac
            JOIN padre p ON p.IdPadre = ac.IdPadre
            {where_c}
            GROUP BY p.IdPadre, Padre
            ORDER BY total DESC
            """,
            tuple(params_c) if params_c else None
        )
        padre_mas = padres_citas[0] if padres_citas else None
        padre_menos = padres_citas[-1] if padres_citas else None

        # ======================
        # GRUPOS / TAREAS
        # ======================
        row_tg = execute_query(
            "SELECT COUNT(*) AS total FROM grupoayudantes g WHERE g.Activo = 1;",
            fetch_one=True
        )
        total_grupos = row_tg["total"] if row_tg else 0

        tareas_por_estado = execute_query(
            """
            SELECT 
              EstadoTarea,
              COUNT(*) AS total
            FROM asignaciontarea
            WHERE Activo = 1
            GROUP BY EstadoTarea
            """
        )

        grupos_tareas = execute_query(
            """
            SELECT 
              g.IdGrupoAyudantes,
              g.Nombre,
              COUNT(at.IdAsignacionTarea) AS total_tareas
            FROM grupoayudantes g
            LEFT JOIN asignaciontarea at
              ON at.IdGrupoVoluntario = g.IdGrupoAyudantes
             AND at.Activo = 1
            WHERE g.Activo = 1
            GROUP BY g.IdGrupoAyudantes, g.Nombre
            ORDER BY total_tareas DESC
            """
        )
        grupo_mas_tareas = grupos_tareas[0] if grupos_tareas else None
        grupo_menos_tareas = grupos_tareas[-1] if grupos_tareas else None

        grupos_integrantes = execute_query(
            """
            SELECT 
              g.IdGrupoAyudantes,
              g.Nombre,
              COUNT(mga.id_miembro) AS total_miembros
            FROM grupoayudantes g
            LEFT JOIN miembro_grupo_ayudantes mga
              ON mga.id_grupo_ayudantes = g.IdGrupoAyudantes
             AND mga.Activo = 1
            WHERE g.Activo = 1
            GROUP BY g.IdGrupoAyudantes, g.Nombre
            ORDER BY total_miembros DESC
            """
        )
        grupo_mas_integrantes = grupos_integrantes[0] if grupos_integrantes else None
        grupo_menos_integrantes = grupos_integrantes[-1] if grupos_integrantes else None

        # ======================
        # FINANZAS
        # ======================
        filtros_m = ["m.Activo = 1"]
        params_m = []
        _add_date_filter(filtros_m, params_m, "m.FechaMovimiento")

        tipo_mov = request.args.get("tipo_mov")  # 1=Ingreso, 2=Egreso, etc.
        if tipo_mov and tipo_mov.isdigit():
            filtros_m.append("m.IdTipoMovimiento = %s")
            params_m.append(int(tipo_mov))

        where_m = "WHERE " + " AND ".join(filtros_m) if filtros_m else ""

        mayor_ingreso = execute_query(
            f"""
            SELECT 
              m.IdMovimiento,
              m.Motivo,
              m.Valor,
              m.FechaMovimiento,
              tm.Descripcion AS TipoMovimiento
            FROM movimientos_caja m
            JOIN tipomovimiento tm ON tm.IdTipoMovimiento = m.IdTipoMovimiento
            {where_m} AND m.IdTipoMovimiento = 1
            ORDER BY m.Valor DESC
            LIMIT 1
            """,
            tuple(params_m) if params_m else None,
            fetch_one=True
        )

        mayor_egreso = execute_query(
            f"""
            SELECT 
              m.IdMovimiento,
              m.Motivo,
              m.Valor,
              m.FechaMovimiento,
              tm.Descripcion AS TipoMovimiento
            FROM movimientos_caja m
            JOIN tipomovimiento tm ON tm.IdTipoMovimiento = m.IdTipoMovimiento
            {where_m} AND m.IdTipoMovimiento = 2
            ORDER BY m.Valor DESC
            LIMIT 1
            """,
            tuple(params_m) if params_m else None,
            fetch_one=True
        )

        row_tot = execute_query(
            f"""
            SELECT
              SUM(CASE WHEN m.IdTipoMovimiento = 1 THEN m.Valor ELSE 0 END) AS total_ingresos,
              SUM(CASE WHEN m.IdTipoMovimiento = 2 THEN m.Valor ELSE 0 END) AS total_egresos
            FROM movimientos_caja m
            {where_m}
            """,
            tuple(params_m) if params_m else None,
            fetch_one=True
        )
        tot_ingresos = float(row_tot["total_ingresos"] or 0) if row_tot else 0.0
        tot_egresos = float(row_tot["total_egresos"] or 0) if row_tot else 0.0

        serie_mensual = execute_query(
            f"""
            SELECT
              DATE_FORMAT(m.FechaMovimiento, '%%Y-%%m') AS periodo,
              SUM(CASE WHEN m.IdTipoMovimiento = 1 THEN m.Valor ELSE 0 END) AS ingresos,
              SUM(CASE WHEN m.IdTipoMovimiento = 2 THEN m.Valor ELSE 0 END) AS egresos
            FROM movimientos_caja m
            {where_m}
            GROUP BY DATE_FORMAT(m.FechaMovimiento, '%%Y-%%m')
            ORDER BY periodo ASC
            """,
            tuple(params_m) if params_m else None
        )

        desde, hasta = _get_date_range()

        return jsonify({
            "success": True,
            "filters": {
                "rango": (request.args.get("rango") or None),
                "desde": desde.isoformat() if desde else None,
                "hasta": hasta.isoformat() if hasta else None,
                "estado_cita": estado_cita,
                "padre": padre,
                "tipo_cita": tipo_cita,
                "tipo_mov": tipo_mov,
            },
            "habitantes": {
                "total_habitantes": total_habitantes,
                "total_familias": total_familias,
                "con_sacramentos": total_con_sac,
                "sin_sacramentos": total_sin_sac,
                "sector_mas": sector_mas,
                "sector_menos": sector_menos,
                "sectores_enfermos": sectores_enfermos,
            },
            "citas": {
                "proximas": proximas,
                "estados": estados_citas,
                "semana_mas": semana_mas,
                "semana_menos": semana_menos,
                "padre_mas": padre_mas,
                "padre_menos": padre_menos,
            },
            "grupos": {
                "total_grupos": total_grupos,
                "tareas_por_estado": tareas_por_estado,
                "grupo_mas_tareas": grupo_mas_tareas,
                "grupo_menos_tareas": grupo_menos_tareas,
                "grupo_mas_integrantes": grupo_mas_integrantes,
                "grupo_menos_integrantes": grupo_menos_integrantes,
            },
            "finanzas": {
                "mayor_ingreso": mayor_ingreso,
                "mayor_egreso": mayor_egreso,
                "totales": {
                    "ingresos": tot_ingresos,
                    "egresos": tot_egresos,
                },
                "serie_mensual": serie_mensual,
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generando resumen global: {str(e)}"
        }), 500


# ==========================================
# 2) DETALLE HABITANTES
#    GET /api/estadisticas/habitantes/
# ==========================================

@estadisticas_bp.route("/habitantes/", methods=["GET"])
@jwt_required()
@require_rol("Administrador")
def estadisticas_habitantes():
    """
    Estadísticas específicas de Habitantes.
    Filtros:
    - rango / desde / hasta     -> DATE(h.FechaRegistro)
    - sector (IdSector)
    - sacramento (IdSacramento)
    """
    try:
        sector = request.args.get("sector")
        sacramento = request.args.get("sacramento")

        filtros = ["h.Activo = 1"]
        params = []

        if sector and sector.isdigit():
            filtros.append("h.IdSector = %s")
            params.append(int(sector))

        join_sac = ""
        if sacramento and sacramento.isdigit():
            join_sac = "JOIN habitante_sacramento hs ON hs.IdHabitante = h.IdHabitante"
            filtros.append("hs.IdSacramento = %s")
            params.append(int(sacramento))

        _add_date_filter(filtros, params, "DATE(h.FechaRegistro)")
        where = "WHERE " + " AND ".join(filtros) if filtros else ""

        row_total = execute_query(
            f"SELECT COUNT(*) AS total FROM habitantes h {join_sac} {where}",
            tuple(params) if params else None,
            fetch_one=True
        )
        total = row_total["total"] if row_total else 0

        total_con_sac = 0
        if total:
            row_con = execute_query(
                f"""
                SELECT COUNT(DISTINCT h.IdHabitante) AS total_con
                FROM habitantes h
                JOIN habitante_sacramento hs ON hs.IdHabitante = h.IdHabitante
                {where}
                """,
                tuple(params) if params else None,
                fetch_one=True
            )
            total_con_sac = row_con["total_con"] if row_con else 0

        total_sin_sac = total - total_con_sac if total else 0

        habitantes_por_sector = execute_query(
            f"""
            SELECT 
              s.IdSector,
              s.Descripcion AS Sector,
              COUNT(*) AS TotalHabitantes
            FROM sector s
            JOIN habitantes h ON h.IdSector = s.IdSector
            {join_sac} {where}
            GROUP BY s.IdSector, s.Descripcion
            ORDER BY TotalHabitantes DESC
            """,
            tuple(params) if params else None
        )
        sector_mas = habitantes_por_sector[0] if habitantes_por_sector else None
        sector_menos = habitantes_por_sector[-1] if habitantes_por_sector else None

        sectores_sacramentos = execute_query(
            f"""
            SELECT 
              s.IdSector,
              s.Descripcion AS Sector,
              COUNT(DISTINCT hs.IdHabitante) AS TotalSacramentados
            FROM sector s
            JOIN habitantes h ON h.IdSector = s.IdSector
            JOIN habitante_sacramento hs ON hs.IdHabitante = h.IdHabitante
            {where}
            GROUP BY s.IdSector, s.Descripcion
            ORDER BY TotalSacramentados DESC
            """,
            tuple(params) if params else None
        )

        filtros_enf = filtros + ["h.TieneImpedimentoSalud = 1"]
        where_enf = "WHERE " + " AND ".join(filtros_enf)
        enfermos_por_sector = execute_query(
            f"""
            SELECT 
              s.IdSector,
              s.Descripcion AS Sector,
              COUNT(*) AS TotalEnfermos
            FROM sector s
            JOIN habitantes h ON h.IdSector = s.IdSector
            {join_sac} {where_enf}
            GROUP BY s.IdSector, s.Descripcion
            ORDER BY TotalEnfermos DESC
            """,
            tuple(params) if params else None
        )

        serie_crecimiento = execute_query(
            f"""
            SELECT 
              DATE(h.FechaRegistro) AS Fecha,
              COUNT(*) AS NuevosHabitantes
            FROM habitantes h
            {join_sac} {where}
            GROUP BY DATE(h.FechaRegistro)
            ORDER BY Fecha ASC
            """,
            tuple(params) if params else None
        )

        reporte = execute_query(
            f"""
            SELECT
              h.IdHabitante,
              CONCAT(h.Nombre, ' ', h.Apellido) AS NombreCompleto,
              h.NumeroDocumento,
              s.Descripcion AS Sector,
              h.Telefono,
              h.CorreoElectronico,
              h.TieneImpedimentoSalud,
              h.FechaRegistro
            FROM habitantes h
            JOIN sector s ON s.IdSector = h.IdSector
            {join_sac} {where}
            ORDER BY h.FechaRegistro DESC
            LIMIT 500
            """,
            tuple(params) if params else None
        )

        return jsonify({
            "success": True,
            "filters": {
                "sector": sector,
                "sacramento": sacramento,
            },
            "totales": {
                "total_habitantes": total,
                "con_sacramentos": total_con_sac,
                "sin_sacramentos": total_sin_sac,
            },
            "sectores": {
                "por_sector": habitantes_por_sector,
                "sector_mas": sector_mas,
                "sector_menos": sector_menos,
                "sacramentos_por_sector": sectores_sacramentos,
                "enfermos_por_sector": enfermos_por_sector,
            },
            "series": {
                "crecimiento": serie_crecimiento
            },
            "reporte": reporte
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generando estadísticas de habitantes: {str(e)}"
        }), 500


# ==========================================
# 3) DETALLE CITAS
#    GET /api/estadisticas/citas/
# ==========================================

@estadisticas_bp.route("/citas/", methods=["GET"])
@jwt_required()
@require_rol("Administrador")
def estadisticas_citas():
    """
    Estadísticas específicas de Citas pastorales.
    Incluye:
    - Próxima cita
    - Citas por estado
    - Semana con más / menos citas
    - Padre con más / menos citas
    - Serie por mes
    - Reporte de citas
    """
    try:
        filtros = ["ac.Activo = 1"]
        params = []

        estado_cita = request.args.get("estado")
        padre = request.args.get("padre")
        tipo_cita = request.args.get("tipo")

        if estado_cita and estado_cita.isdigit():
            filtros.append("ac.IdEstadoCita = %s")
            params.append(int(estado_cita))

        if padre and padre.isdigit():
            filtros.append("ac.IdPadre = %s")
            params.append(int(padre))

        if tipo_cita and tipo_cita.isdigit():
            filtros.append("ac.IdTipoCita = %s")
            params.append(int(tipo_cita))

        _add_date_filter(filtros, params, "ac.Fecha")
        where = "WHERE " + " AND ".join(filtros) if filtros else ""

        proxima = execute_query(
            f"""
            SELECT 
              ac.IdAsignacionCita,
              ac.Fecha,
              TIME_FORMAT(ac.Hora, '%%H:%%i') AS Hora,
              ac.NombreSolicitante,
              ac.CelularSolicitante,
              CONCAT(p.Nombre, ' ', p.Apellido) AS Padre,
              ec.Descripcion AS Estado,
              tc.Descripcion AS TipoCita
            FROM asignacioncita ac
            LEFT JOIN padre p ON p.IdPadre = ac.IdPadre
            LEFT JOIN estadocita ec ON ec.IdEstadoCita = ac.IdEstadoCita
            LEFT JOIN tipocita tc ON tc.IdTipoCita = ac.IdTipoCita
            {where} AND ac.Fecha >= CURDATE()
            ORDER BY ac.Fecha ASC, ac.Hora ASC
            LIMIT 1
            """,
            tuple(params) if params else None,
            fetch_one=True
        )

        totales_estado = execute_query(
            f"""
            SELECT 
              ec.Descripcion AS Estado,
              COUNT(*) AS total
            FROM asignacioncita ac
            JOIN estadocita ec ON ec.IdEstadoCita = ac.IdEstadoCita
            {where}
            GROUP BY ec.Descripcion
            """,
            tuple(params) if params else None
        )

        semanas = execute_query(
            f"""
            SELECT 
              YEARWEEK(ac.Fecha, 1) AS SemanaISO,
              MIN(ac.Fecha) AS FechaInicio,
              MAX(ac.Fecha) AS FechaFin,
              COUNT(*) AS TotalCitas
            FROM asignacioncita ac
            {where}
            GROUP BY YEARWEEK(ac.Fecha, 1)
            ORDER BY TotalCitas DESC
            """,
            tuple(params) if params else None
        )
        semana_mas = semanas[0] if semanas else None
        semana_menos = semanas[-1] if semanas else None

        padres = execute_query(
            f"""
            SELECT 
              p.IdPadre,
              CONCAT(p.Nombre, ' ', p.Apellido) AS Padre,
              COUNT(*) AS TotalCitas
            FROM asignacioncita ac
            JOIN padre p ON p.IdPadre = ac.IdPadre
            {where}
            GROUP BY p.IdPadre, Padre
            ORDER BY TotalCitas DESC
            """,
            tuple(params) if params else None
        )
        padre_mas_citas = padres[0] if padres else None
        padre_menos_citas = padres[-1] if padres else None

        serie_mensual = execute_query(
            f"""
            SELECT 
              DATE_FORMAT(ac.Fecha, '%%Y-%%m') AS Periodo,
              COUNT(*) AS TotalCitas
            FROM asignacioncita ac
            {where}
            GROUP BY DATE_FORMAT(ac.Fecha, '%%Y-%%m')
            ORDER BY Periodo ASC
            """,
            tuple(params) if params else None
        )

        reporte = execute_query(
            f"""
            SELECT
              ac.IdAsignacionCita,
              ac.Fecha,
              TIME_FORMAT(ac.Hora, '%%H:%%i') AS Hora,
              ac.NombreSolicitante,
              ac.CelularSolicitante,
              CONCAT(p.Nombre, ' ', p.Apellido) AS Padre,
              ec.Descripcion AS Estado,
              tc.Descripcion AS TipoCita
            FROM asignacioncita ac
            LEFT JOIN padre p ON p.IdPadre = ac.IdPadre
            LEFT JOIN estadocita ec ON ec.IdEstadoCita = ac.IdEstadoCita
            LEFT JOIN tipocita tc ON tc.IdTipoCita = ac.IdTipoCita
            {where}
            ORDER BY ac.Fecha DESC, ac.Hora DESC
            LIMIT 500
            """,
            tuple(params) if params else None
        )

        return jsonify({
            "success": True,
            "filters": {
                "estado": estado_cita,
                "padre": padre,
                "tipo": tipo_cita,
            },
            "totales": {
                "por_estado": totales_estado
            },
            "resumen": {
                "proxima": proxima,
                "semana_mas": semana_mas,
                "semana_menos": semana_menos,
                "padre_mas_citas": padre_mas_citas,
                "padre_menos_citas": padre_menos_citas,
            },
            "series": {
                "citas_por_mes": serie_mensual,
            },
            "reporte": reporte
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generando estadísticas de citas: {str(e)}"
        }), 500


# ==========================================
# 4) DETALLE GRUPOS / TAREAS
#    GET /api/estadisticas/grupos/
# ==========================================

@estadisticas_bp.route("/grupos/", methods=["GET"])
@jwt_required()
@require_rol("Administrador")
def estadisticas_grupos():
    """
    Estadísticas de Grupos de Ayudantes y Tareas.
    """
    try:
        filtros = ["at.Activo = 1"]
        params = []

        grupo = request.args.get("grupo")
        estado_tarea = request.args.get("estado")

        if grupo and grupo.isdigit():
            filtros.append("at.IdGrupoVoluntario = %s")
            params.append(int(grupo))

        if estado_tarea:
            filtros.append("at.EstadoTarea = %s")
            params.append(estado_tarea)

        _add_date_filter(filtros, params, "DATE(at.FechaAsignacion)")
        where = "WHERE " + " AND ".join(filtros) if filtros else ""

        row_total = execute_query(
            f"""
            SELECT COUNT(*) AS total
            FROM asignaciontarea at
            {where}
            """,
            tuple(params) if params else None,
            fetch_one=True
        )
        total_tareas = row_total["total"] if row_total else 0

        tareas_por_estado = execute_query(
            f"""
            SELECT 
              at.EstadoTarea,
              COUNT(*) AS total
            FROM asignaciontarea at
            {where}
            GROUP BY at.EstadoTarea
            """,
            tuple(params) if params else None
        )

        grupos_tareas = execute_query(
            f"""
            SELECT 
              g.IdGrupoAyudantes,
              g.Nombre,
              COUNT(at.IdAsignacionTarea) AS TotalTareas
            FROM grupoayudantes g
            LEFT JOIN asignaciontarea at
              ON at.IdGrupoVoluntario = g.IdGrupoAyudantes
             AND at.Activo = 1
            WHERE g.Activo = 1
            GROUP BY g.IdGrupoAyudantes, g.Nombre
            ORDER BY TotalTareas DESC
            """,
            None
        )
        grupo_mas_tareas = grupos_tareas[0] if grupos_tareas else None
        grupo_menos_tareas = grupos_tareas[-1] if grupos_tareas else None

        grupos_integrantes = execute_query(
            """
            SELECT 
              g.IdGrupoAyudantes,
              g.Nombre,
              COUNT(mga.id_miembro) AS TotalIntegrantes
            FROM grupoayudantes g
            LEFT JOIN miembro_grupo_ayudantes mga
              ON mga.id_grupo_ayudantes = g.IdGrupoAyudantes
             AND mga.Activo = 1
            WHERE g.Activo = 1
            GROUP BY g.IdGrupoAyudantes, g.Nombre
            ORDER BY TotalIntegrantes DESC
            """
        )
        grupo_mas_integrantes = grupos_integrantes[0] if grupos_integrantes else None
        grupo_menos_integrantes = grupos_integrantes[-1] if grupos_integrantes else None

        serie_mensual = execute_query(
            f"""
            SELECT 
              DATE_FORMAT(at.FechaAsignacion, '%%Y-%%m') AS Periodo,
              COUNT(*) AS TotalTareas
            FROM asignaciontarea at
            {where}
            GROUP BY DATE_FORMAT(at.FechaAsignacion, '%%Y-%%m')
            ORDER BY Periodo ASC
            """,
            tuple(params) if params else None
        )

        reporte = execute_query(
            f"""
            SELECT
              at.IdAsignacionTarea,
              at.TituloTarea,
              at.DescripcionTarea,
              at.FechaAsignacion,
              at.EstadoTarea,
              g.Nombre AS Grupo
            FROM asignaciontarea at
            LEFT JOIN grupoayudantes g ON g.IdGrupoAyudantes = at.IdGrupoVoluntario
            {where}
            ORDER BY at.FechaAsignacion DESC
            LIMIT 500
            """,
            tuple(params) if params else None
        )

        return jsonify({
            "success": True,
            "filters": {
                "grupo": grupo,
                "estado": estado_tarea,
            },
            "totales": {
                "total_tareas": total_tareas,
                "por_estado": tareas_por_estado,
            },
            "resumen": {
                "grupo_mas_tareas": grupo_mas_tareas,
                "grupo_menos_tareas": grupo_menos_tareas,
                "grupo_mas_integrantes": grupo_mas_integrantes,
                "grupo_menos_integrantes": grupo_menos_integrantes,
            },
            "series": {
                "tareas_por_mes": serie_mensual
            },
            "reporte": reporte
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generando estadísticas de grupos: {str(e)}"
        }), 500


# ==========================================
# 5) DETALLE FINANZAS
#    GET /api/estadisticas/finanzas/
# ==========================================

@estadisticas_bp.route("/finanzas/", methods=["GET"])
@jwt_required()
@require_rol("Administrador")
def estadisticas_finanzas():
    """
    Estadísticas de Finanzas (movimientos de caja).
    Incluye:
    - Mayor ingreso / egreso
    - Totales por tipo
    - Serie mensual ingresos vs egresos
    - Distribución por categoría (concepto)
    - Reporte de movimientos
    """
    try:
        filtros = ["m.Activo = 1"]
        params = []

        tipo_mov = request.args.get("tipo_mov")  # 1=Ingreso,2=Egreso,...
        concepto = request.args.get("concepto")  # IdConceptoTransaccion

        if tipo_mov and tipo_mov.isdigit():
            filtros.append("m.IdTipoMovimiento = %s")
            params.append(int(tipo_mov))

        if concepto and concepto.isdigit():
            filtros.append("m.IdConceptoTransaccion = %s")
            params.append(int(concepto))

        _add_date_filter(filtros, params, "m.FechaMovimiento")
        where = "WHERE " + " AND ".join(filtros) if filtros else ""

        mayor_ingreso = execute_query(
            f"""
            SELECT 
              m.IdMovimiento,
              m.Motivo,
              m.Valor,
              m.FechaMovimiento,
              tm.Descripcion AS TipoMovimiento
            FROM movimientos_caja m
            JOIN tipomovimiento tm ON tm.IdTipoMovimiento = m.IdTipoMovimiento
            {where} AND m.IdTipoMovimiento = 1
            ORDER BY m.Valor DESC
            LIMIT 1
            """,
            tuple(params) if params else None,
            fetch_one=True
        )

        mayor_egreso = execute_query(
            f"""
            SELECT 
              m.IdMovimiento,
              m.Motivo,
              m.Valor,
              m.FechaMovimiento,
              tm.Descripcion AS TipoMovimiento
            FROM movimientos_caja m
            JOIN tipomovimiento tm ON tm.IdTipoMovimiento = m.IdTipoMovimiento
            {where} AND m.IdTipoMovimiento = 2
            ORDER BY m.Valor DESC
            LIMIT 1
            """,
            tuple(params) if params else None,
            fetch_one=True
        )

        row_tot = execute_query(
            f"""
            SELECT
              SUM(CASE WHEN m.IdTipoMovimiento = 1 THEN m.Valor ELSE 0 END) AS TotalIngresos,
              SUM(CASE WHEN m.IdTipoMovimiento = 2 THEN m.Valor ELSE 0 END) AS TotalEgresos
            FROM movimientos_caja m
            {where}
            """,
            tuple(params) if params else None,
            fetch_one=True
        )
        total_ingresos = float(row_tot["TotalIngresos"] or 0) if row_tot else 0.0
        total_egresos = float(row_tot["TotalEgresos"] or 0) if row_tot else 0.0

        serie_mensual = execute_query(
            f"""
            SELECT
              DATE_FORMAT(m.FechaMovimiento, '%%Y-%%m') AS Periodo,
              SUM(CASE WHEN m.IdTipoMovimiento = 1 THEN m.Valor ELSE 0 END) AS Ingresos,
              SUM(CASE WHEN m.IdTipoMovimiento = 2 THEN m.Valor ELSE 0 END) AS Egresos
            FROM movimientos_caja m
            {where}
            GROUP BY DATE_FORMAT(m.FechaMovimiento, '%%Y-%%m')
            ORDER BY Periodo ASC
            """,
            tuple(params) if params else None
        )

        distribucion_concepto = execute_query(
            f"""
            SELECT
              ct.IdConceptoTransaccion,
              ct.Descripcion AS Concepto,
              SUM(m.Valor) AS Total
            FROM movimientos_caja m
            JOIN conceptotransaccion ct ON ct.IdConceptoTransaccion = m.IdConceptoTransaccion
            {where}
            GROUP BY ct.IdConceptoTransaccion, ct.Descripcion
            ORDER BY Total DESC
            """,
            tuple(params) if params else None
        )

        reporte = execute_query(
            f"""
            SELECT
              m.IdMovimiento,
              m.FechaMovimiento,
              m.Motivo,
              m.Valor,
              tm.Descripcion AS TipoMovimiento,
              ct.Descripcion AS Concepto
            FROM movimientos_caja m
            JOIN tipomovimiento tm ON tm.IdTipoMovimiento = m.IdTipoMovimiento
            JOIN conceptotransaccion ct ON ct.IdConceptoTransaccion = m.IdConceptoTransaccion
            {where}
            ORDER BY m.FechaMovimiento DESC, m.IdMovimiento DESC
            LIMIT 500
            """,
            tuple(params) if params else None
        )

        return jsonify({
            "success": True,
            "filters": {
                "tipo_mov": tipo_mov,
                "concepto": concepto,
            },
            "totales": {
                "ingresos": total_ingresos,
                "egresos": total_egresos,
            },
            "resumen": {
                "mayor_ingreso": mayor_ingreso,
                "mayor_egreso": mayor_egreso,
            },
            "series": {
                "ingresos_egresos_mensual": serie_mensual,
            },
            "distribucion": {
                "por_concepto": distribucion_concepto,
            },
            "reporte": reporte
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generando estadísticas de finanzas: {str(e)}"
        }), 500
