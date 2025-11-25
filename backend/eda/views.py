from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.core.cache import cache
from .models import EdaSession, EdaChart
from .serializers import FileUploadSerializer, EdaSessionSerializer, EdaChartSerializer
from .services.data_processor import DataProcessor
from .services.chart_generator import ChartGenerator
from .services.ai_insights import AiInsightsGenerator
import os
import pandas as pd


class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            
            try:
                session = EdaSession.objects.create(
                    filename=file.name,
                    file_path=f"uploads/{file.name}"
                )
                
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, file.name)
                
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)

                df = pd.read_csv(file_path)
                
                session.row_count = len(df)
                session.column_count = len(df.columns)
                session.file_path = f"uploads/{file.name}"
                session.save()
                
                processor = DataProcessor(df)
                cleaned_df = processor.clean_data()
                summary = processor.get_summary()
                
                session_serializer = EdaSessionSerializer(session, context={'request': request})
                
                return Response({
                    'message': 'File uploaded successfully',
                    'session': session_serializer.data,
                    'summary': summary
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Error processing file: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EdaChartsView(APIView):
    def get(self, request, session_id):
        try:
            session = EdaSession.objects.get(session_id=session_id)
            charts = session.charts.all()
            serializer = EdaChartSerializer(charts, many=True, context={'request': request})
            
            return Response({
                'session_id': str(session_id),
                'charts': serializer.data
            }, status=status.HTTP_200_OK)
            
        except EdaSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


class AiInsightsView(APIView):
    def get(self, request, session_id):
        try:
            session = EdaSession.objects.get(session_id=session_id)
            
            if session.insights:
                return Response({
                    'session_id': str(session_id),
                    'insights': session.insights
                }, status=status.HTTP_200_OK)
            
            file_path = os.path.join(settings.MEDIA_ROOT, session.file_path)
            df = pd.read_csv(file_path)
            
            processor = DataProcessor(df)
            cleaned_df = processor.clean_data()
            summary = processor.get_summary()
            
            chart_generator = ChartGenerator(
                cleaned_df,
                session.session_id,
                settings.EDA_OUTPUT_DIR,
                theme='light'
            )
            
            chart_paths = chart_generator.generate_intelligent_charts_for_ai(summary)
            
            for chart_info in chart_paths:
                EdaChart.objects.get_or_create(
                    session=session,
                    chart_type=chart_info['type'],
                    chart_path=chart_info['path'],
                    defaults={'column_name': chart_info.get('column')}
                )
            
            ai_generator = AiInsightsGenerator(settings.GEMINI_API_KEY)
            
            numeric_cols = cleaned_df.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) >= 2:
                selected_cols = ai_generator.select_pairplot_columns(cleaned_df, summary)
                chart_generator._generate_pairplot(selected_cols)
                
                if chart_generator.charts:
                    latest_chart = chart_generator.charts[-1]
                    EdaChart.objects.get_or_create(
                        session=session,
                        chart_type=latest_chart['type'],
                        chart_path=latest_chart['path'],
                        defaults={'column_name': latest_chart.get('column')}
                    )
            
            insights = ai_generator.generate_insights(cleaned_df, summary, chart_paths)
            
            session.insights = insights
            session.save()
            
            return Response({
                'session_id': str(session_id),
                'insights': insights
            }, status=status.HTTP_200_OK)
            
        except EdaSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Error generating insights: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionListView(APIView):
    def get(self, request):
        sessions = EdaSession.objects.all()
        serializer = EdaSessionSerializer(sessions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SessionDetailView(APIView):
    def get(self, request, session_id):
        try:
            session = EdaSession.objects.get(session_id=session_id)
            serializer = EdaSessionSerializer(session, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except EdaSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


class ColumnInfoView(APIView):
    def get(self, request, session_id):
        try:
            session = EdaSession.objects.get(session_id=session_id)
            file_path = os.path.join(settings.MEDIA_ROOT, session.file_path)
            df = pd.read_csv(file_path)
            
            processor = DataProcessor(df)
            cleaned_df = processor.clean_data()
            
            import numpy as np
            numeric_cols = cleaned_df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = cleaned_df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            columns_info = []
            for col in cleaned_df.columns:
                col_type = 'numeric' if col in numeric_cols else 'categorical'
                columns_info.append({
                    'name': col,
                    'type': col_type,
                    'null_count': int(cleaned_df[col].isnull().sum()),
                    'unique_count': int(cleaned_df[col].nunique())
                })
            
            return Response({
                'session_id': str(session_id),
                'columns': columns_info,
                'numeric_columns': numeric_cols,
                'categorical_columns': categorical_cols
            }, status=status.HTTP_200_OK)
            
        except EdaSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Error getting column info: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateCustomChartsView(APIView):
    def post(self, request, session_id):
        try:
            import numpy as np
            session = EdaSession.objects.get(session_id=session_id)
            file_path = os.path.join(settings.MEDIA_ROOT, session.file_path)
            df = pd.read_csv(file_path)
            
            selected_columns = request.data.get('columns', [])
            theme = request.data.get('theme', 'light')
            
            if not selected_columns:
                return Response({'error': 'No columns selected'}, status=status.HTTP_400_BAD_REQUEST)
            
            processor = DataProcessor(df)
            cleaned_df = processor.clean_data()
            
            valid_columns = [col for col in selected_columns if col in cleaned_df.columns]
            
            if not valid_columns:
                return Response({
                    'error': 'Selected columns are not available in the processed data.',
                    'charts_available': False
                }, status=status.HTTP_400_BAD_REQUEST)
            
            filtered_df = cleaned_df[valid_columns]
            
            chart_generator = ChartGenerator(
                filtered_df,
                session.session_id,
                settings.EDA_OUTPUT_DIR,
                theme=theme
            )
            
            numeric_cols = filtered_df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = filtered_df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            if len(numeric_cols) == 0 and len(categorical_cols) == 0:
                return Response({
                    'error': 'No valid columns selected.',
                    'charts_available': False
                }, status=status.HTTP_400_BAD_REQUEST)
            
            charts = []
            
            for col in numeric_cols:
                chart_generator._generate_histogram(col)
                chart_generator._generate_boxplot(col)
                chart_generator._generate_distribution_plot(col)
            
            for col in categorical_cols:
                chart_generator._generate_bar_chart(col)
            
            if len(numeric_cols) >= 2:
                chart_generator._generate_correlation_heatmap(numeric_cols)
                chart_generator._generate_pairplot(numeric_cols)
            
            new_charts = chart_generator.charts
            
            if len(new_charts) == 0:
                return Response({
                    'error': 'No charts could be generated.',
                    'charts_available': False
                }, status=status.HTTP_400_BAD_REQUEST)
            
            for chart_info in new_charts:
                EdaChart.objects.create(
                    session=session,
                    chart_type=chart_info['type'],
                    chart_path=chart_info['path'],
                    column_name=chart_info.get('column')
                )
            
            all_charts = session.charts.all()
            serializer = EdaChartSerializer(all_charts, many=True, context={'request': request})
            
            return Response({
                'session_id': str(session_id),
                'message': f'Generated {len(new_charts)} charts',
                'charts': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except EdaSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Error generating charts: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateOnDemandChartsView(APIView):
    def post(self, request, session_id):
        try:
            session = EdaSession.objects.get(session_id=session_id)
            file_path = os.path.join(settings.MEDIA_ROOT, session.file_path)
            df = pd.read_csv(file_path)

            x_axis = request.data.get('x_axis')
            y_axis = request.data.get('y_axis')
            chart_types = request.data.get('chart_types')
            theme = request.data.get('theme', 'light')

            processor = DataProcessor(df)
            cleaned_df = processor.clean_data()

            requested = [c for c in (x_axis, y_axis) if c]
            valid_cols = [c for c in requested if c in cleaned_df.columns]
            if requested and not valid_cols:
                return Response({
                    'error': 'Requested axis columns are not available.',
                    'charts_generated': False
                }, status=status.HTTP_400_BAD_REQUEST)

            existing_charts = self._check_existing_charts(session, x_axis, y_axis, chart_types)
            
            if existing_charts['all_exist']:
                return Response({
                    'session_id': str(session_id),
                    'charts_generated': False,
                    'message': 'These plots are already in your library!',
                    'existing_charts': existing_charts['charts'],
                    'charts': existing_charts['charts']
                }, status=status.HTTP_200_OK)
            
            chart_generator = ChartGenerator(cleaned_df, session.session_id, settings.EDA_OUTPUT_DIR, theme=theme)
            generated = chart_generator.generate_on_demand_charts(x_axis=x_axis, y_axis=y_axis, chart_types=chart_types)

            saved = []
            newly_generated = []
            
            for chart_info in chart_generator.charts:
                column_name = chart_info.get('column', '')
                existing = EdaChart.objects.filter(
                    session=session,
                    chart_type=chart_info['type'],
                    column_name=column_name
                ).first()
                
                if not existing:
                    EdaChart.objects.create(
                        session=session,
                        chart_type=chart_info['type'],
                        chart_path=chart_info['path'],
                        column_name=column_name
                    )
                    newly_generated.append({
                        'type': chart_info['type'],
                        'path': chart_info['path'],
                        'column': column_name
                    })

                saved.append({
                    'type': chart_info['type'],
                    'path': chart_info['path'],
                    'column': column_name
                })

            response_message = f"Generated {len(newly_generated)} new chart(s)"
            if len(newly_generated) < len(saved):
                duplicates = len(saved) - len(newly_generated)
                response_message += f" ({duplicates} already existed)"

            return Response({
                'session_id': str(session_id),
                'charts_generated': True,
                'newly_generated': len(newly_generated),
                'message': response_message,
                'charts': saved
            }, status=status.HTTP_200_OK)

        except EdaSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error generating on-demand charts: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _check_existing_charts(self, session, x_axis, y_axis, chart_types):
        if not chart_types:
            return {'all_exist': False, 'charts': []}
        
        existing_charts = []
        
        for chart_type in chart_types:
            if x_axis and y_axis:
                column_pattern = f"{x_axis}_vs_{y_axis}"
            elif x_axis:
                column_pattern = x_axis
            elif y_axis:
                column_pattern = y_axis
            else:
                continue
            
            existing = EdaChart.objects.filter(
                session=session,
                chart_type=chart_type,
                column_name__icontains=column_pattern
            ).first()
            
            if existing:
                existing_charts.append({
                    'type': existing.chart_type,
                    'path': existing.chart_path,
                    'column': existing.column_name
                })
        
        all_exist = len(existing_charts) == len(chart_types) if chart_types else False
        
        return {
            'all_exist': all_exist,
            'charts': existing_charts
        }
