from dash import Dash, html, dcc, Input, Output, State, ctx, dash_table
from dash.exceptions import PreventUpdate
import base64
import io
import pandas as pd
import numpy as np
import plotly.express as px

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
# https://dash.plotly.com/deployment
# https://medium.com/innovation-res/how-to-build-an-ap504828p-using-dash-plotly-and-python-and-deploy-it-to-aws-5d8d2c7bd652
# https://datasciencecampus.github.io/deploy-dash-with-gcp/
# https://www.programonaut.com/7-ways-to-host-your-web-application-for-free/
# on Heroku https://ekimetrics.github.io/blog/dash-deployment/
# Render https://www.youtube.com/watch?v=H16dZMYmvqo

app = Dash(__name__)  # , external_stylesheets=external_stylesheets
server = app.server
app.title = 'Characteristic curve Dashboard'
# app_color = {"graph_bg": "#082255", "graph_line": "#007ACE"}
# app_color = {"graph_bg": '#79f7d4', "graph_line": "#007ACE"}
app_color = {"graph_bg": '#A3E4D7', "graph_line": "#007ACE"}
app_margins = {'left': 20, 'right': 20, 'top': 20, 'bottom': 20}

app.layout = html.Div([
    html.H1(id='Header', children='Characteristic curve'),

    html.Div(className='row',
             style={'display': 'flex'},
             children=[
                 html.Div([dcc.Upload(id='upload-curve', children=html.Button('Upload curve'))]),
                 html.Div([dcc.Upload(id='upload-meas', children=html.Button('Upload measurements'))]),
                 html.Div([html.Button('Download results', id='btn-download'), dcc.Download(id='download')]),
                 html.Div([html.Button('Restore curve', id='btn-restore')])
             ]),
    html.Br(),
    html.Div(className='row', style={'display': 'flex'},
             children=[html.Label('Polynomial degree:', style={'font-weight': 'bold', 'text-align': 'center',
                                                               'padding': '5px'}),
                       html.Div([dcc.Dropdown(id='drop-degree', options=[1, 2, 3, 4, 5, 6, 7],
                                              value=3, clearable=False)]),
                       ]),

    html.Div(
        [
            # curve
            html.Div(
                [
                    html.H5('Characteristic curve', className='graph__title'),
                    dcc.Graph(
                        id='graph-curve',
                        figure=dict(
                            layout=dict(
                                plot_bgcolor=app_color["graph_bg"],
                                paper_bgcolor=app_color["graph_bg"],
                            ),
                        ),
                    )
                ],
                className='two-thirds column wind__speed__container',
            ),
            # table
            html.Div(
                [
                    html.H5('Table', className='graph__title'),
                    # https://dash.plotly.com/datatable/data-formatting
                    dash_table.DataTable(
                        id='interactive-table',
                        columns=[{'name': 'count', 'id': 'count', 'type': 'numeric',
                                  'format': dash_table.Format.Format(precision=2,
                                                                     scheme=dash_table.Format.Scheme.fixed)
                                  },
                                 {'name': 'mag', 'id': 'mag', 'type': 'numeric',
                                  'format': dash_table.Format.Format(precision=3,
                                                                     scheme=dash_table.Format.Scheme.fixed)
                                  }],
                        # page_action='none',
                        page_size=100,
                        style_cell={'fontSize': 20, 'height': 30, 'textAlign': 'center'},
                        style_header={'backgroundColor': 'paleturquoise', 'fontWeight': 'bold'},
                        style_data={'backgroundColor': 'lavender'},
                        # style_table={'overflowY': 'auto'},
                        style_table={'height': '450px', 'overflowY': 'auto'},
                        fixed_rows={'headers': True},

                    )
                    # dcc.Graph(id='restable')
                ],
                className='one-third column wind__speed__container',
            ),
        ],
        className="app__content",
    ),

    dcc.Store(id='store-fit'),
    dcc.Store(id='store-curve'),
    dcc.Store(id='store-curve-back'),
    dcc.Store(id='store-meas')
])


def parse_curve(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), comment='#', header=None, names=['count', 'mag'])
    return df


def parse_meas(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), comment='#', header=None, names=['count', 'mag'])
    return df


@app.callback(Output('store-meas', 'data'),
              Input('upload-meas', 'contents'),
              Input('store-fit', 'data'),
              State('store-meas', 'data'),
              prevent_initial_call=True)
def handle_meas(uploaded_meas, jsonified_fit, jsonified_meas):
    print('Handle_meas')
    print('context =', ctx.triggered_id)

    if ctx.triggered_id == 'upload-meas':
        print('Uploading measurements')
        dfm = parse_meas(uploaded_meas)
        dfm['mag'] = 0.0
    else:  # new fit stored
        if jsonified_fit is None:
            raise PreventUpdate
        if jsonified_meas is None:  # get it from store-meas
            print('jsonified_meas is None')
            raise PreventUpdate
        dfm = pd.read_json(jsonified_meas, orient='split')

    if jsonified_fit is not None:
        dff = pd.read_json(jsonified_fit, orient='split')
        fit = np.array(dff[0])
        dfm['mag'] = np.poly1d(fit)(dfm['count'])

    return dfm.to_json(orient='split')


@app.callback(Output('store-curve-back', 'data'),
              Input('upload-curve', 'contents'),  # and Store fit in the safe-box
              prevent_initial_call=True)
def update_curve(curve_data):
    if curve_data is None:
        print('curve_data is None')
        raise PreventUpdate
    print('Parse curve')
    df = parse_curve(curve_data)
    return df.to_json(orient='split')


@app.callback(Output('store-curve', 'data'),
              Input('store-curve-back', 'data'),  # and Store fit
              Input('btn-restore', 'n_clicks'),  # restore curve
              Input('graph-curve', 'clickData'),  # edit curve
              State('store-curve', 'data'),
              prevent_initial_call=True)
def update_curve(jsonified_curve_back, _, click_data, jsonified_curve):
    print('Store curve after modifying')
    if ctx.triggered_id == 'graph-curve':
        print('graph-curve has been clicked')
        if click_data['points'][0]['curveNumber'] != 0:
            raise PreventUpdate
        df = pd.read_json(jsonified_curve, orient='split')
        df.drop(index=click_data['points'][0]['pointIndex'], inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df.to_json(orient='split')
    # if ctx.triggered_id == 'btn-restore':  # restore curve from the safe-box
    return jsonified_curve_back  # restore curve


@app.callback(Output('store-fit', 'data'),
              Input('store-curve', 'data'),
              Input('drop-degree', 'value'),
              prevent_initial_call=True)
def fit_poly(jsonified_curve, degree):
    print('fit_poly')
    if jsonified_curve is None:
        raise PreventUpdate
    if degree is None:
        raise PreventUpdate
    df = pd.read_json(jsonified_curve, orient='split')
    fit = np.polyfit(df['count'], df['mag'], int(degree))
    dff = pd.DataFrame(fit)
    print('Jsonification of fit')
    return dff.to_json(orient='split')


@app.callback(Output('interactive-table', 'data'),
              Input('store-meas', 'data'),
              prevent_initial_call=False)
def draw_table(jsonified_meas):
    if jsonified_meas is not None:
        df = pd.read_json(jsonified_meas, orient='split')
        # values = [df['count'], df['mag']]
        data = df.to_dict('records')
    else:
        raise PreventUpdate
    return data


@app.callback(Output('graph-curve', 'figure'),
              Input('store-fit', 'data'),
              Input('store-curve', 'data'),
              Input('store-meas', 'data'),
              Input('interactive-table', 'active_cell'),
              prevent_initial_call=False)
def plot_curve(jsonified_fit, jsonified_curve, jsonified_meas, active_cell):
    print('plot_curve')
    if jsonified_curve is None:
        print('No curve')
        fig = px.scatter()
    else:
        df = pd.read_json(jsonified_curve, orient='split')
        fig = px.scatter(df, x='count', y='mag')  # , trendline='ols')
        if jsonified_fit is not None:
            print('jsonified_fit is not None')
            dff = pd.read_json(jsonified_fit, orient='split')
            fit = np.array(dff[0])
            x_fit = np.linspace(df['count'].min(), df['count'].max(), 50)
            fig.add_scatter(x=x_fit, y=np.poly1d(fit)(x_fit), name='fit', mode='lines',
                            hoverinfo='skip', line=dict(color='Green'), showlegend=True)
        if jsonified_meas is not None:
            dfm = pd.read_json(jsonified_meas, orient='split')
            xm = dfm['count']
            ym = dfm['mag']
            fig.add_scatter(x=xm, y=ym, name='vars', mode='markers',
                            # marker=dict(color='Orange'),
                            marker=dict(size=10, color='Orange'),
                            showlegend=True)
            if active_cell:
                xms = dfm.iloc[active_cell['row']]['count']
                yms = dfm.iloc[active_cell['row']]['mag']
                fig.add_scatter(x=[xms], y=[yms], name='selected', mode='markers',
                                marker=dict(size=15, color='yellow'),
                                showlegend=True)

    fig.update_layout({'paper_bgcolor': app_color['graph_bg'],
                       'plot_bgcolor': app_color['graph_bg'],
                       'margin': dict(t=app_margins['top'], b=app_margins['bottom'],
                                      l=app_margins['left'], r=app_margins['right']),
                       'font': dict(size=15)})
    print('Figure is ready')
    return fig


@app.callback(
    Output('download', 'data'),
    Input('btn-download', 'n_clicks'),
    State('store-meas', 'data'),
    prevent_initial_call=True
)
def download_meas(_, jsonified_meas):
    # return dcc.send_data_frame(df.to_csv, 'my.txt')
    if jsonified_meas is None:
        raise PreventUpdate
    dfm = pd.read_json(jsonified_meas, orient='split')
    # return dict(content=dfm, filename="hello.txt")
    return dcc.send_data_frame(dfm.to_csv, "results.csv", sep=' ', float_format='%.3f', index=False)
    # return dict(content='my string', filename="hello.txt")


if __name__ == '__main__':
    app.run(debug=True)
