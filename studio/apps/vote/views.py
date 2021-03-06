from studio.apps.vote import vote
from studio.models import VoteInfo, VoteCandidates, VoteVotes, db
from studio.utils.cache import cache
from studio.apps.vote import get_candidate_all_info, get_candidate_info, get_vote_info
from flask import url_for, redirect, render_template, request, flash, jsonify, Markup, send_file, g
from flask import current_app
from faker import Faker
import time
import random
import datetime
f = Faker(locale='zh_CN')


@vote.route("/")
@cache.memoize(20)
def root():
    voteinfo_all = VoteInfo.query.all()
    return render_template('vote_index.html', info_list=voteinfo_all, title="投票列表")


@vote.route('/<int:vote_id>', methods=["GET"])
def vote_page(vote_id):
    datetime_now = datetime.datetime.now()
    vote_info = get_vote_info(vote_id=vote_id)
    if vote_info.disabled:
        flash('投票已暂停')
        return render_template('vote_result.html', vote_info=vote_info, title="投票结果")


    if (vote_info.start_at > datetime_now or
            (vote_info.start_at != vote_info.end_at and vote_info.end_at < datetime_now))\
            and not vote_info.show_raw_vote_on_expire:
        flash('不在有效的投票时间段内')
        return render_template('vote_result.html', vote_info=vote_info, title="投票结果")

    voted = VoteVotes.query.filter(VoteVotes.ip == request.headers.get('X-Forwarded-For')).filter(
        VoteVotes.vote_id == vote_id).first()
    if voted and not vote_info.show_raw_vote_on_voted:
        flash("您已投过票")
        return render_template('vote_result.html', vote_info=vote_info, title="投票结果")

    candidate_all = get_candidate_all_info(vote_id=vote_id)

    if vote_info.shuffle:
        random.shuffle(candidate_all)

    return render_template(
        'vote_vote_page.html',
        candidate_all=candidate_all,
        vote_info=vote_info,
        can_vote=False if
        (voted or not vote_info.show_raw_vote_on_expire or not vote_info.show_raw_vote_on_voted) else True)


@vote.route('/candidate')
def show_candidate():
    cid = request.values.get('cid')
    if not cid:
        return ""
    c = get_candidate_info(c_id=cid)
    vote_info = get_vote_info(vote_id=c.vote_id)
    return render_template("vote_candidate.html", candidate=c, vote_info=vote_info)


@vote.route('/stats/<int:vote_id>')
def show_stats(vote_id):
    vote_info = get_vote_info(vote_id=vote_id)
    if not vote_info.show_stats:
        flash("当前投票结果不可见")
        return render_template("vote_result.html", vote_info=vote_info, title="结果不可见")

    candidates_all = sorted(get_candidate_all_info(vote_id=vote_id), key=lambda x: x.votes, reverse=True)
    return render_template('vote_stats.html', vote_info=vote_info, candidates_all=candidates_all)


def get_tickets_and_candidates(vote_id: int, lim=5):
    candidate_info = VoteCandidates.query.filter(VoteCandidates.vote_id == vote_id).order_by(
        VoteCandidates.votes.desc()).limit(lim).all()
    vote_tickets = VoteVotes.query.filter(VoteVotes.vote_id == vote_id).all()
    return (vote_tickets, candidate_info)


def tostamp(dt1):
    Unixtime = time.mktime(time.strptime(dt1.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S'))
    return Unixtime


# @vote.route('/statistics/<int:vote_id>')
# def get_vote_stats(vote_id):
#     lim = 5 if request.values.get('lim') is None else int(request.values.get('lim'))
#     res = {}
#     vote_tickets, candidate_info = get_tickets_and_candidates(vote_id, lim=lim)
#     for c in candidate_info:
#         key = str(c.id) + "-" + c.title
#         res[key] = []
#         for v in vote_tickets:
#             if v.candidate == c.id:
#                 res[key].append(int(tostamp(v.created_at)))
#     return jsonify(res)


# @vote.route('/getcsv/<int:vote_id>')
# def getcsv(vote_id):
#     res = {}
#     data = {}
#     head = []
#     vote_tickets, candidate_info = get_tickets_and_candidates(vote_id, lim=80)
#     for c in candidate_info:
#         key = str(c.id) + "-" + c.title
#         res[key] = []
#         for v in vote_tickets:
#             if v.candidate == c.id:
#                 res[key].append(int(tostamp(v.created_at)))
#     _start = 1607601600
#     _step = 600 if request.values.get('step') is None else int(request.values.get('step'))
#     _end = 1608136800
#     head.append('姓名')
#     for i in range(0, int((_end - _start) / 600)):
#         timeArray = time.localtime(_start + _step * i)
#         otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
#         head.append(otherStyleTime)
#     names = list(res.keys())
#     for i in range(len(names)):
#         data[names[i]] = []
#         now = _start
#         step = _step
#         end = _end
#         while now <= end:
#             count = 0
#             for j in range(len(res[names[i]])):
#                 if res[names[i]][j] < now:
#                     count = count + 1
#             data[names[i]].append(count)
#             now = now + step
#     fname = os.path.join(
#         os.getcwd(), 'studio', 'apps', 'vote', 'static', 'csv',
#         'vote_' + str(vote_id) + '_' + time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(time.time())) + '.csv')
#     with codecs.open(fname, 'wb', "gbk") as csvfile:
#         csv_writer = csv.writer(csvfile)
#         csv_writer.writerow(head)
#         for k in data:
#             csv_writer.writerow([k] + data[k])
#     return send_file(fname, as_attachment=True, attachment_filename=fname)


@vote.route('/<int:vote_id>', methods=["POST"])
def vote_handler(vote_id):
    voted = VoteVotes.query.filter(VoteVotes.ip == request.headers.get('X-Forwarded-For')).filter(
        VoteVotes.vote_id == vote_id).first()
    if voted:
        current_app.logger.warn('vote_attempt:' + request.remote_addr)
        return jsonify({"success": False, "details": "您已投过票"})
    if not current_app.hcaptcha.verify():
        return jsonify({"success": False, "details": "验证码无效"})
    vote_list = request.get_json()
    current_app.logger.debug('candidates:' + str(request.form.getlist('candidates')))
    vote_list = request.form.getlist('candidates')
    vs = []
    id_list = []
    for v in vote_list:
        _v = VoteVotes(ip=request.headers.get('X-Forwarded-For') or request.remote_addr,
                       candidate=int(v),
                       vote_id=vote_id)
        vs.append(_v)
        id_list.append(_v.candidate)
    db.session.add_all(vs)
    VoteCandidates.query.filter(VoteCandidates.id.in_(id_list)).update({VoteCandidates.votes: VoteCandidates.votes + 1},
                                                                       synchronize_session=False)
    db.session.commit()
    return redirect(url_for('vote.vote_result_handler', vote_id=vote_id))


@vote.route('/result/<int:vote_id>', methods=['GET'])
def vote_result_handler(vote_id):
    flash("投票成功")
    return render_template('vote_result.html', vote_id=vote_id, title="投票结果")
