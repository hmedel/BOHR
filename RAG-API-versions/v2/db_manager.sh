#!/bin/bash
# Script de gestión de base de datos para RAG v2
# Proporciona comandos fáciles para tareas comunes

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Activar conda environment
eval "$(conda shell.bash hook)"
conda activate bohrenv

function show_menu() {
    clear
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         GESTOR DE BASE DE DATOS - RAG v2                  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}1.${NC} Listar usuarios"
    echo -e "${GREEN}2.${NC} Listar usuarios con estadísticas detalladas"
    echo -e "${GREEN}3.${NC} Ver estadísticas de la base de datos"
    echo -e "${GREEN}4.${NC} Limpiar solo conversaciones y mensajes"
    echo -e "${GREEN}5.${NC} Limpiar solo exámenes"
    echo -e "${GREEN}6.${NC} Limpiar analytics (query_logs, student_progress)"
    echo -e "${GREEN}7.${NC} Limpiar usuarios (mantener admin)"
    echo -e "${GREEN}8.${NC} ${RED}LIMPIAR TODO (mantener admin)${NC}"
    echo -e "${GREEN}9.${NC} ${RED}LIMPIAR TODO (incluyendo admin)${NC}"
    echo -e "${GREEN}10.${NC} Exportar usuarios a CSV"
    echo -e "${GREEN}0.${NC} Salir"
    echo ""
    echo -n "Selecciona una opción: "
}

function press_enter() {
    echo ""
    read -p "Presiona ENTER para continuar..."
}

while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            clear
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${BLUE}            LISTA DE USUARIOS${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            python list_users.py
            press_enter
            ;;
        2)
            clear
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${BLUE}     USUARIOS CON ESTADÍSTICAS DETALLADAS${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            python list_users.py --details
            press_enter
            ;;
        3)
            clear
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${BLUE}     ESTADÍSTICAS DE LA BASE DE DATOS${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            python clean_database.py --stats
            press_enter
            ;;
        4)
            clear
            echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            echo -e "${YELLOW}⚠️  LIMPIAR CONVERSACIONES Y MENSAJES${NC}"
            echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            python clean_database.py --conversations
            press_enter
            ;;
        5)
            clear
            echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            echo -e "${YELLOW}⚠️  LIMPIAR EXÁMENES${NC}"
            echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            python clean_database.py --exams
            press_enter
            ;;
        6)
            clear
            echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            echo -e "${YELLOW}⚠️  LIMPIAR ANALYTICS${NC}"
            echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
            python clean_database.py --analytics
            press_enter
            ;;
        7)
            clear
            echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
            echo -e "${RED}⚠️⚠️  LIMPIAR USUARIOS (mantener admin)${NC}"
            echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
            python clean_database.py --users --keep-admin
            press_enter
            ;;
        8)
            clear
            echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
            echo -e "${RED}🔴🔴🔴  LIMPIAR TODO (mantener admin)${NC}"
            echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
            python clean_database.py --all --keep-admin
            press_enter
            ;;
        9)
            clear
            echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
            echo -e "${RED}🔴🔴🔴  LIMPIAR TODO (incluyendo admin)${NC}"
            echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
            python clean_database.py --all --no-keep-admin
            press_enter
            ;;
        10)
            clear
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            echo -e "${BLUE}     EXPORTAR USUARIOS A CSV${NC}"
            echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
            python list_users.py --export
            press_enter
            ;;
        0)
            echo -e "${GREEN}¡Hasta luego!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Opción inválida. Intenta de nuevo.${NC}"
            sleep 2
            ;;
    esac
done