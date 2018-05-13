import plotly
import plotly.graph_objs as go
from flask import session, render_template

from flask_monitoringdashboard import blueprint, config
from flask_monitoringdashboard.core.auth import secure
from flask_monitoringdashboard.core.colors import get_color
from flask_monitoringdashboard.database import session_scope
from flask_monitoringdashboard.database.count_group import get_value
from flask_monitoringdashboard.database.tests import get_test_names, get_test_cnt_avg, get_test_suites, \
    get_test_measurements, get_test_cnt_avg_current, get_suite_measurements, get_last_tested_times
from flask_monitoringdashboard.database.tests_grouped import get_tests_grouped, get_endpoint_names


@blueprint.route('/testmonitor/<end>')
@secure
def endpoint_test_details(end):
    """
    Shows the performance results for one specific unit test.
    :param end: the name of the unit test for which the results should be shown
    :return:
    """
    return render_template('fmd_testmonitor/testresult.html', link=config.link, session=session, name=end)
    # return render_template('fmd_testmonitor/testresult.html', link=config.link, session=session, name=end,
    #                            boxplot=get_boxplot(end))


@blueprint.route('/testmonitor')
@secure
def testmonitor():
    """
    Gives an overview of the unit test performance results and the endpoints that they hit.
    :return:
    """
    with session_scope() as db_session:
        from numpy import median

        endpoint_test_combinations = get_tests_grouped(db_session)

        # tests_latest = count_requests_group(db_session, FunctionCall.time > week_ago)
        # tests = count_requests_group(db_session)
        # median_latest = get_endpoint_data_grouped(db_session, median, FunctionCall.time > week_ago)
        # median = get_endpoint_data_grouped(db_session, median)
        tested_times = get_last_tested_times(db_session, endpoint_test_combinations)

        result = []
        for endpoint in get_endpoint_names(db_session):
            result.append({
                'name': endpoint,
                'color': get_color(endpoint),
                # 'tests-latest-version': get_value(tests_latest, endpoint),
                # 'tests-overall': get_value(tests, endpoint),
                # 'median-latest-version': get_value(median_latest, endpoint),
                # 'median-overall': get_value(median, endpoint),
                'tests-latest-version': 0,
                'tests-overall': 0,
                'median-latest-version': 0,
                'median-overall': 0,
                'last-tested': get_value(tested_times, endpoint, default=None)
            })

        tests_grouped_by_endpoint = {}
        endpoint_colors = {}
        for combination in endpoint_test_combinations:
            if combination.endpoint not in tests_grouped_by_endpoint:
                tests_grouped_by_endpoint[combination.endpoint] = []
                endpoint_colors[combination.endpoint] = get_color(combination.endpoint)
            tests_grouped_by_endpoint[combination.endpoint].append(combination.test_name)

        return render_template('fmd_testmonitor/testmonitor.html', tests=get_test_names(db_session),
                               results=get_test_cnt_avg(db_session), groups=tests_grouped_by_endpoint,
                               colors=endpoint_colors, result=result,
                               res_current_version=get_test_cnt_avg_current(db_session, config.version),
                               boxplot=get_boxplot())


def get_boxplot(test=None):
    """
    Generates a box plot visualization for the unit test performance results.
    :param test: if specified, generate box plot for a specific test, otherwise, generate for all tests
    :return:
    """
    data = []
    with session_scope() as db_session:
        suites = get_test_suites(db_session)
    if not suites:
        return None
    for s in suites:
        if test:
            values = [str(c.execution_time) for c in get_test_measurements(db_session, name=test, suite=s.suite)]
        else:
            values = [str(c.execution_time) for c in get_suite_measurements(db_session, suite=s.suite)]

        data.append(go.Box(
            x=values,
            name="{0} ({1})".format(s.suite, len(values))))

    layout = go.Layout(
        autosize=True,
        height=350 + 40 * len(suites),
        plot_bgcolor='rgba(249,249,249,1)',
        showlegend=False,
        title='Execution times for every Travis build',
        xaxis=dict(title='Execution time (ms)'),
        yaxis=dict(
            title='Build (measurements)',
            autorange='reversed'
        )
    )

    return plotly.offline.plot(go.Figure(data=data, layout=layout), output_type='div', show_link=False)
