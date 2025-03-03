import logging
import json
from typing import Dict, Any
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config.settings import OUTPUT_DIR
from core.exceptions import ReportGenerationError

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)



class ReportGenerator:
    """Générateur de rapports d'évaluation avec visualisations"""
    
    def __init__(self):
        """Initialise le générateur de rapports"""
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ReportGenerator initialized successfully")

    def generate_report(self, evaluation_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Génère un rapport d'évaluation détaillé avec visualisations
        
        Args:
            evaluation_results (Dict[str, Any]): Résultats de l'évaluation
            
        Returns:
            Dict[str, str]: Chemins des fichiers générés
            
        Raises:
            ReportGenerationError: Si une erreur survient lors de la génération
        """
        try:
            # Création du timestamp pour les noms de fichiers
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Préparation des données pour DataFrame
            criteria_data = self._prepare_criteria_data(evaluation_results)
            
            # Création des visualisations
            fig = self._create_visualizations(criteria_data)
            
            # Génération des fichiers de rapport
            report_files = self._save_reports(evaluation_results, criteria_data, fig, timestamp)
            
            logger.info("Report generation completed successfully")
            return report_files
            
        except Exception as e:
            error_msg = f"Failed to generate report: {str(e)}"
            logger.error(error_msg)
            raise ReportGenerationError(error_msg)

    def _prepare_criteria_data(self, evaluation_results: Dict[str, Any]) -> pd.DataFrame:
        """
        Prépare les données pour l'analyse
        
        Args:
            evaluation_results (Dict[str, Any]): Résultats de l'évaluation
            
        Returns:
            pd.DataFrame: DataFrame avec les données préparées
        """
        criteria_data = []
        
        for criterion, stats in evaluation_results['criteria_scores'].items():
            percentage = (stats['score'] / stats['total']) * 100 if stats['total'] > 0 else 0
            success_rate = (stats['success_count'] / stats['questions_count']) * 100 if stats['questions_count'] > 0 else 0
            
            criteria_data.append({
                'Criterion': criterion,
                'Score': percentage,
                'Success_Rate': success_rate,
                'Questions': stats['questions_count'],
                'Successful_Responses': stats['success_count']
            })
        
        return pd.DataFrame(criteria_data)

    def _create_visualizations(self, df_criteria: pd.DataFrame) -> go.Figure:
        """
        Crée les visualisations des résultats
        
        Args:
            df_criteria (pd.DataFrame): DataFrame des critères
            
        Returns:
            go.Figure: Figure Plotly avec les visualisations
        """
        fig = go.Figure()

        # Graphique radar des scores
        fig.add_trace(go.Scatterpolar(
            r=df_criteria['Score'],
            theta=df_criteria['Criterion'],
            fill='toself',
            name='Score (%)'
        ))

        # Ajout du taux de succès
        fig.add_trace(go.Scatterpolar(
            r=df_criteria['Success_Rate'],
            theta=df_criteria['Criterion'],
            fill='toself',
            name='Taux de succès (%)'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            title='Évaluation du modèle par critère',
            showlegend=True
        )

        return fig

    def _save_reports(self, 
                     evaluation_results: Dict[str, Any],
                     df_criteria: pd.DataFrame,
                     fig: go.Figure,
                     timestamp: str) -> Dict[str, str]:
        """
        Sauvegarde les différents formats de rapport
        
        Args:
            evaluation_results (Dict[str, Any]): Résultats complets
            df_criteria (pd.DataFrame): DataFrame des critères
            fig (go.Figure): Figure Plotly
            timestamp (str): Horodatage pour les noms de fichiers
            
        Returns:
            Dict[str, str]: Chemins des fichiers générés
        """
        # Création des chemins de fichiers
        html_path = self.output_dir / f"evaluation_report_{timestamp}.html"
        csv_path = self.output_dir / f"evaluation_scores_{timestamp}.csv"
        json_path = self.output_dir / f"evaluation_results_{timestamp}.json"
        viz_path = self.output_dir / f"evaluation_viz_{timestamp}.html"

        # Génération du rapport HTML
        html_content = self._generate_html_report(evaluation_results, df_criteria)
        html_path.write_text(html_content, encoding='utf-8')

        # Sauvegarde des données CSV
        df_criteria.to_csv(csv_path, index=False)

        # Sauvegarde des résultats JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation_results, f, ensure_ascii=False, indent=2)

        # Sauvegarde de la visualisation
        fig.write_html(str(viz_path))

        return {
            'html_report': str(html_path),
            'csv_data': str(csv_path),
            'json_results': str(json_path),
            'visualization': str(viz_path)
        }

    def _generate_html_report(self, 
                            evaluation_results: Dict[str, Any],
                            df_criteria: pd.DataFrame) -> str:
        """
        Génère le contenu du rapport HTML
        
        Args:
            evaluation_results (Dict[str, Any]): Résultats de l'évaluation
            df_criteria (pd.DataFrame): DataFrame des critères
            
        Returns:
            str: Contenu HTML du rapport
        """
        return f"""
        <html>
        <head>
            <title>Rapport d'Évaluation du Modèle</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Rapport d'Évaluation du Modèle</h1>
            
            <h2>Résumé Global</h2>
            <ul>
                <li>Score Total: {evaluation_results['total_score']}</li>
                <li>Taux de Succès Global: {evaluation_results['success_rate']:.2f}%</li>
                <li>Nombre d'Erreurs: {evaluation_results['error_count']}</li>
            </ul>

            <h2>Détails par Critère</h2>
            {df_criteria.to_html(index=False, float_format=lambda x: '{:.2f}'.format(x))}
            
            <h2>Métriques Avancées</h2>
            <pre>{json.dumps(evaluation_results['advanced_metrics'], indent=2)}</pre>
        </body>
        </html>
        """