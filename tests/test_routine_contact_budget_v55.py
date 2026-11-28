"""#140: run the real contact assessor and routine prefix/local selection fragments.

Native path, actor, LOS and position scoring are controlled fixtures; no
gameplay prediction or native WOTC execution is claimed.
"""
from pathlib import Path
import re
from types import SimpleNamespace as NS
import unittest

from test_live_unit_stats import UCArray, translate_body
from test_ui_gating import function_body
from uc_math import load_uc_function

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / "AutoplayXCom2/Src/AutoplayXCom2/Classes"
CONTACT = CLASSES / "APX_ContactEnvelope.uc"
MISSION = CLASSES / "APX_MissionPlanner.uc"
CONTROLLER = CLASSES / "APX_Controller.uc"
PATROL = CLASSES / "APX_PatrolAmbushPlanner.uc"


def compile_fragment(name, params, body, env):
    """Adapt only the syntax of the actual bounded UC fragments."""
    for cls, alias in (("APX_ContactEnvelope", "Contact"),
                       ("APX_ConcealmentPlanner", "Concealment"),
                       ("APX_ExplosiveCoverKnowledge", "Cover"),
                       ("X2PathSolver", "PathSolver")):
        body = body.replace("class'" + cls + "'.static.", alias + ".")
        body = body.replace("class'" + cls + "'.default.", alias + "Defaults.")
    body = body.replace("class'XComGameState_ChallengeData'", "'challenge'")
    body = re.sub(r"\x60log\(.*?\);", "Log();", body, flags=re.S)
    body = re.sub(r"--(Remaining\w+);", r"\1 -= 1;", body)
    body = body.replace("for (Step = 1; Step < Path.Length; ++Step)",
                        "for Step in range(1, Path.Length)")
    for name_ in ("KnownUnits", "KnownInteractives"):
        body = body.replace(f"for (Index = 0; Index < {name_}.Length; ++Index)",
                            f"for Index in range({name_}.Length)")
    body = re.sub(r"\belse\s+if\s*\(", "if (__UC_ELIF__ && ", body)
    body = re.sub(r"\belse\b", "if (__UC_ELSE__)", body)
    for target, source in (("RiskyRoute", "Path"), ("LocalFallbackPath", "CandidatePath"),
                           ("Path", "CandidatePath"), ("Path", "RiskyRoute"),
                           ("DeferredBudgetPrefix", "Path"), ("Path", "DeferredBudgetPrefix"),
                           ("Path", "LocalFallbackPath"), ("MemoryFallbackPath", "Path"),
                           ("MemoryFallbackPath", "CandidatePath"), ("Path", "MemoryFallbackPath"),
                           ("BestPath", "CandidatePath")):
        body = body.replace(f"{target} = {source};", f"{target} = UCArray({source});")
    body = body.replace("bInspectContact ? 1 : 0", "1 if bInspectContact else 0")
    # Replace the specific conditional expression used for the first-blue ticket.
    body = re.sub(r"\(bSingleBlue && ContactStatus == 0\s*&& bTempoCurrentPathSafe\) \? 1 : 0",
                  "(1 if (bSingleBlue && ContactStatus == 0 && bTempoCurrentPathSafe) else 0)", body)
    body = body.replace("bMemoryFallbackFirstClear ? 1 : 0", "1 if bMemoryFallbackFirstClear else 0")
    body = body.replace("(bInspectContact && !bUsedLocalFallback) ? 1 : 0",
                        "(1 if (bInspectContact && !bUsedLocalFallback) else 0)")
    body = body.replace("(iAcceptedRoutine > 0 && bSingleBlue && bBestBlueFullyClear) ? 1 : 0",
                        "(1 if (iAcceptedRoutine > 0 && bSingleBlue && bBestBlueFullyClear) else 0)")
    body = re.sub(r"ContactStatus = Contact.AssessRoute\((.*?)\);",
                  r"ContactStatus, RemainingContactDetectors, RemainingContactTiles, RemainingContactLOS, ContactReason = Contact.AssessRoute(\1);",
                  body, flags=re.S)
    def concat(match):
        """Adapt the real diagnostic's UC string operators."""
        parts=re.split(r"\s*([@$])\s*",match[1])
        value="str("+parts[0]+")"
        for op,part in zip(parts[1::2],parts[2::2]):
            value+=(' + " " + ' if op=="@" else " + ")+"str("+part+")"
        return "MoveDiagnostic = "+value+";"
    body=re.sub(r"MoveDiagnostic\s*=\s*([^;]*[@$][^;]*);",concat,body)
    body=re.sub(r"\+\+(\w+);",r"\1 += 1;",body)
    translated = re.sub(r"\bif __UC_ELIF__\s+and\s+", "elif ", translate_body(body))
    translated = translated.replace("if __UC_ELSE__:", "else:")
    code = "def " + name + "(" + params + "):\n" + translated
    ns = dict(env, UCArray=UCArray, string=str)
    exec(compile(code, name, "exec"), ns)
    return ns[name]


class DetectorFixture:
    """Stock-state doubles: one nearby detector and seven remote ones."""
    def __init__(self):
        """Keep all eight known references and count actual native pair reads."""
        self.pair_reads = 0
        self.los_reads = 0
        self.detectors = {i: NS(TileLocation=1000 if i == 1 else 10000+i*1000,
                                UnitSize=1, bRemovedFromPlay=False,
                                GetMyTemplate=lambda: NS(bIsCosmetic=False),
                                IsAlive=lambda: True, IsIncapacitated=lambda: False,
                                IsCivilian=lambda: False, GetVisibilityRadius=lambda: 300)
                          for i in range(1,9)}
        self.refs = UCArray([NS(ObjectID=i) for i in self.detectors])
        self.world = NS(IsTileOutOfRange=lambda _:False,
                        GetPositionFromTileCoordinates=lambda tile:tile,
                        CanSeeTileToTile=self.see)
        self.history = NS(GetGameStateForObjectID=self.lookup,
                          GetSingleGameStateObjectForClass=lambda *_:NS())
        self.unknown_los = False

    def lookup(self, object_id):
        """Count each real assessor pair lookup."""
        self.pair_reads += 1
        return self.detectors.get(object_id)

    def see(self, origin, destination, visibility):
        """Native geometry fixture, not a prediction of game LOS."""
        self.los_reads += 1
        visibility.DefaultTargetDist = (origin-destination)**2
        return not self.unknown_los and abs(origin-destination) <= 300

    def soldier(self, number=1, concealed=False):
        """Give a routine unit native legal path origin and current visibility state."""
        return NS(ObjectID=number, TileLocation=0, UnitSize=1,
                  IsConcealed=lambda:concealed, IsEnemyUnit=lambda _:True,
                  UnitBreaksConcealment=lambda _:True,
                  GetConcealmentDetectionDistance=lambda _:300,
                  GetMyTemplate=lambda:NS(bCanTakeCover=False),
                  NumActionPoints=lambda:2)


class RoutineContactBudgetTests(unittest.TestCase):
    """Exercise the actual assessor, existing route ranking and work limits."""

    def setUp(self):
        """Prepare real functions and native test doubles."""
        self.fixture = DetectorFixture()
        self.contact = CONTACT.read_text(encoding="utf-8-sig")
        self.choose = function_body(MISSION.read_text(encoding="utf-8-sig"), "ChooseMove")
        self.budget = load_uc_function(CONTACT, "RoutineDetectorBudget")
        self.preflight = load_uc_function(CONTACT, "HasRoutinePairBudget")
        self.penalty = load_uc_function(CONTACT, "PathStatusPenalty")
        self.penalty.__globals__["default"] = NS(CautionRoutePenalty=24, UnknownRoutePenalty=8)
        self.env = dict(XWORLD=self.fixture.world, XCOMHISTORY=self.fixture.history,
                        XComGameState_Unit=lambda x:x, XComGameState_InteractiveObject=lambda x:x,
                        METERSTOUNITS=lambda x:x, VSizeSq=lambda x:x*x, Square=lambda x:x*x,
                        name=str, string=str, MakeVisibility=NS,
                        SupportsAnchorVisibility=load_uc_function(CONTACT,"SupportsAnchorVisibility"),
                        ConcealedContactPossible=load_uc_function(CONTACT,"ConcealedContactPossible"),
                        CombineRouteStatus=load_uc_function(CONTACT,"CombineRouteStatus"),
                        HasRoutinePairBudget=self.preflight)
        body = function_body(self.contact,"AssessRoute")
        body = body.replace("Reason = SnapshotReason;", "Visibility = MakeVisibility();\nReason = SnapshotReason;")
        body = re.sub(r"return (-1|0|1|Status);",
                      r"return (\1,RemainingDetectors,RemainingTiles,RemainingLOS,Reason);", body)
        self.assess = compile_fragment("Assess",
            "Soldier,Path,KnownUnits,KnownInteractives,bSnapshotComplete,SnapshotReason,HorizonAITurns,RemainingDetectors,RemainingTiles,RemainingLOS,Reason,bRequireFullPairBudget",
            body,self.env)

    def test_budget_and_preflight_boundaries(self):
        """Separate snapshot cap from the bounded routine pair-work limit."""
        for configured, expected in ((0,1024),(-1,1024),(1,1),(64,64),(1024,1024),(100000,1024)):
            self.assertEqual(expected,self.budget(configured))
        for args,expected in (((8,8,64),True),((9,8,64),False),((128,8,1024),True),
                              ((129,0,1024),False),((1,65,1024),False),
                              ((0,8,1024),False),((1,-1,1024),False),
                              ((1,0,1),True),((1,0,0),False)):
            self.assertEqual(expected,self.preflight(*args))

    def test_preflight_saves_work_for_finishable_alternative(self):
        """Insufficient pairs cannot consume the tail of the shared budget."""
        unit = self.fixture.soldier()
        long = UCArray([0,-100,-200,-300])
        short = UCArray([0,-100,-200])
        result = self.assess(unit,long,self.fixture.refs,UCArray(),True,"snapshot",0,16,128,512,"",True)
        self.assertEqual((-1,16,128,512,"detector_pair_budget"),result)
        self.assertEqual(0,self.fixture.pair_reads)
        result = self.assess(unit,short,self.fixture.refs,UCArray(),True,"snapshot",0,*result[1:4],"",True)
        self.assertEqual((0,0,126,512,"clear_current_snapshot_only"),result)
        self.assertEqual(16,self.fixture.pair_reads)
        result = self.assess(unit,short,self.fixture.refs,UCArray(),True,"snapshot",0,*result[1:4],"",True)
        self.assertEqual((-1,0,126,512,"decision_budget"),result)

    def test_middle_contact_and_unknown_native_geometry(self):
        """A contact on the middle tile cannot be erased by the clear endpoint."""
        unit = self.fixture.soldier()
        route = UCArray([0,100,200,300,1000,2000,2100,2200,2300])
        result = self.assess(unit,route,self.fixture.refs,UCArray(),True,"snapshot",0,1024,128,512,"",True)
        self.assertEqual(1,result[0])
        self.assertEqual("revealed_native_geometry_los",result[-1])
        self.assertEqual(25,self.fixture.pair_reads)
        self.fixture.unknown_los = True
        result = self.assess(unit,route,self.fixture.refs,UCArray(),True,"snapshot",0,1024,128,512,"",True)
        self.assertEqual(-1,result[0])
        self.assertEqual("native_peek_unverified",result[-1])
        self.assertEqual(-1,self.assess(unit,route,self.fixture.refs,UCArray(),False,"incomplete",0,1024,128,512,"",True)[0])

    def choose_route(self, unit, path, candidates, remaining, results, preserve=False,
                     local_gain=12, second=False, cover_risk=0, stealth_risk=False, cohesion_gain=0):
        """One invocation of the real prefix/local/fallback flow with shared native doubles."""
        def assess(unit,path,units,interactives,complete,reason,horizon,pairs,tiles,los,detail,require):
            """Model UC out parameters and capture the work of each candidate."""
            before = self.fixture.pair_reads
            result = self.assess(unit,path,units,interactives,complete,reason,horizon,pairs,tiles,los,detail,require)
            remaining[:] = result[1:4]
            results.append((unit.ObjectID,result[0],self.fixture.pair_reads-before,result[-1],path[-1]))
            return result
        env = dict(Contact=NS(AssessRoute=assess,PathStatusPenalty=self.penalty),
                   ApplyConstructiveSoftPenalty=load_uc_function(MISSION,"ApplyConstructiveSoftPenalty"),
                   ScoreOrdinaryRouteCandidate=load_uc_function(MISSION,"ScoreOrdinaryRouteCandidate"),
                   ScoreRouteAdvance=load_uc_function(MISSION,"ScoreRouteAdvance"),
                   SquadPositionScore=lambda _,tile:cohesion_gain if tile!=unit.TileLocation else 0,
                   FMin=min,FMax=max,Log=lambda:None,
                   BlueRouteExposureSafe=lambda *_:True,BlueRouteExplosiveSafe=lambda *_:True,
                   Concealment=NS(RouteConcealmentPenalty=lambda *_:0,
                                  InspectPathRisk=lambda _,route,*__:stealth_risk and len(route)<len(path)),
                   Cover=NS(InspectRiskAtTile=lambda *_:cover_risk),
                   ConcealmentDefaults=NS(ConcealmentRiskPenalty=18))
        # Actual prefix scoring, with equal native cohesion and no extra risk.
        score_start = self.choose.index("Score = ScoreRouteAdvance(")
        score_end = self.choose.index(";",score_start)+1
        start = self.choose.index("if (bInspectContact)\n                {\n                    ContactStatus")
        end = self.choose.index("UnitVisualizer.m_kReachableTilesCache.GetAllPathableTiles",start)
        prefix = self.choose[start:end].rstrip()
        # The enclosing exposure/route blocks were opened before this fragment.
        for _ in range(3):
            prefix = prefix[:prefix.rfind("}")].rstrip()
        start = self.choose.index("if (bSafe)", self.choose.index("++UnsafePathRejected"))
        end = self.choose.index("\n    }\n    if (!bSecondBlue && Path.Length < 2 && DeferredBudgetPrefix.Length > 1)",start)
        local = self.choose[start:end]
        gain_start=self.choose.rindex("if (CandidateScore <= BestScore)",0,start)
        gain_end=self.choose.index("CandidatePath.Length = 0;",gain_start)
        gain_gate=self.choose[gain_start:gain_end]
        fallback = self.choose[end+len("\n    }\n"):]
        body = (
            "RiskyRoute = UCArray(); RiskyRouteScore = 0; RiskyRouteCoverRisk = 0;"
            "RiskyContactStatus = -1; RiskyContactReason = \"\";"
            "DeferredBudgetPrefix = UCArray(); DeferredBudgetScore = 0;"
            "MemoryFallbackPath = UCArray(); MemoryFallbackScore = 0; MemoryFallbackRank = 0;"
            "ContactReason = \"\"; ConcealmentRiskReason = \"\"; bInspectContact = true; bSingleBlue = !bSecondBlue;"
            "CoverRisk = 0.0; bCoverUrgent = false; RouteTempo = none;"
            "VisibleEnemies = UCArray(); MeleeThreatReaches = UCArray(); ThreatWeights = UCArray();"
            "CurrentRisk = 0; RemainingTempoCoverChecks = 128; RemainingCoverChecks = 128; RemainingConcealmentChecks = 6;"
            "iFirstBlueClear = 0; iAcceptedRoutine = 0; bCombatGoal = false;"
            + self.choose[score_start:score_end] + prefix
            + "CurrentScore = 0; BestScore = 4; LocalFallbackScore = 4; BestRisk = 0;"
            "LocalFallbackPath = UCArray(); BestContactStatus = -1;"
            "bBestBlueFullyClear = false; bUsedLocalFallback = false;"
            "SampleCount = 0; EndpointRejected = 0; GainRejected = 0;"
            "NativePathRejected = 0; UnsafePathRejected = 0; bPrefixFound = true;"
            "MoveDiagnostic = \"\";"
            "for CandidatePath in Candidates {"
            "Tile = CandidatePath[CandidatePath.Length - 1]; CandidateScore = LocalGain; CandidateRisk = 0; bSafe = true;"
            + gain_gate + local + "}" + fallback)
        body = body.replace("return true;","return (true,Path,Score,iAcceptedRoutine,iFirstBlueClear);")
        body = body.replace("return false;","return (false,Path,Score,iAcceptedRoutine,iFirstBlueClear);")
        return compile_fragment("Choose",
            "UnitState,Path,Candidates,ContactUnits,ContactInteractives,bContactSnapshotComplete,ContactSnapshotReason,RemainingContactDetectors,RemainingContactTiles,RemainingContactLOS,bPreservePatrolContactBudget,LocalGain,bSecondBlue,bConcealmentUrgent",
            body,env)(unit,UCArray(path),[UCArray(p) for p in candidates],self.fixture.refs,UCArray(),
                      True,"snapshot",*remaining,preserve,local_gain,second,not stealth_risk)

    def controller_selection(self, proposals, initial=2, reject=()):
        """Execute the actual controller comparison and native-validation gate."""
        make = function_body(CONTROLLER.read_text(encoding="utf-8-sig"),"MakeDecision")
        start = make.index("if (bCandidateMove\n            && TraceCandidateMove")
        end = make.index("if (MissionMoveOutcome != \"selected\"",start)
        gate = make[start:end]
        body = ("BestScore = Initial; BestUnit = none; BestPath = UCArray(); BestLocations = UCArray();"
                "bHavePlan = true; bSelectedFirstBlue = false; bContactSearch = false;"
                "iCandidateEmergencyRoute = 0; MissionMovePlanner = \"mission\"; CandidateRouteGoal = 0;"
                "for Proposal in Proposals {"
                "UnitState = Proposal.unit; bCandidateMove = Proposal.found;"
                "CandidatePath = Proposal.path; Score = Proposal.score;"
                "iCandidateRoutine = Proposal.routine; iCandidateFirstBlue = Proposal.ticket;"
                +gate+"} return (BestUnit,BestPath,BestScore,bSelectedFirstBlue);")
        env = dict(TraceCandidateMove=lambda *_:True,
                   CanUseMove=lambda unit,*_:unit.ObjectID not in reject)
        return compile_fragment("Select","Proposals,Initial",body,env)(proposals,initial)

    def run_squad(self, configured, preserve, alternative=True, paths=None):
        """Share budgets across actual route flows, then choose through the controller gate."""
        remaining = [configured,128,512]
        results,proposals = [],[]
        if paths is None:
            paths = [[0]+[-100*i for i in range(1,length+1)] for length in (12,8,8,8)]
            paths[-1] = [0,100,200,300,1000,2000,2100,2200,2300]
        for n,path in enumerate(paths,1):
            unit = self.fixture.soldier(n)
            candidates = [[0,-100,-200,-300,-400,-500,-600]] if alternative and n==len(paths) else []
            found,chosen,score,routine,ticket = self.choose_route(unit,path,candidates,remaining,results,preserve)
            proposals.append(NS(unit=unit,found=found,path=chosen,score=score,routine=routine,ticket=ticket))
        return results,proposals,remaining,self.controller_selection(proposals)

    def test_four_soldiers_old_and_new_budget(self):
        """Compare real started/resolved inspections and controller's actual choice."""
        old,proposals,left,chosen = self.run_squad(64,True)
        self.assertEqual((4,1,0),(len(old),sum(x[2]>0 for x in old),sum(x[1]>=0 for x in old)))
        self.assertEqual(0,left[0])
        self.assertEqual(2300,proposals[-1].path[-1])
        self.assertEqual((1,-1200,17,False),(chosen[0].ObjectID,chosen[1][-1],chosen[2],chosen[3]))
        self.fixture.pair_reads = self.fixture.los_reads = 0
        new,proposals,left,chosen = self.run_squad(self.budget(1024),False)
        self.assertEqual((5,5,5),(len(new),sum(x[2]>0 for x in new),sum(x[1]>=0 for x in new)))
        self.assertEqual([0,0,0,1,0],[x[1] for x in new])
        self.assertEqual((4,-600,32,True),(chosen[0].ObjectID,chosen[1][-1],chosen[2],chosen[3]))
        self.assertEqual(297,self.fixture.pair_reads)
        self.assertEqual(727,left[0])
        self.assertGreaterEqual(left[1],0)
        self.assertGreaterEqual(left[2],0)
        # Native CanUseMove and stronger competing action still win.
        self.assertEqual(1,self.controller_selection(proposals,reject=(4,))[0].ObjectID)
        self.assertIsNone(self.controller_selection(proposals,initial=80)[0])

    def test_only_legal_caution_prefix_remains_usable(self):
        """No qualified alternative does not force the squad to idle."""
        results,proposals,_,_ = self.run_squad(self.budget(1024),False,False)
        self.assertEqual(1,results[-1][1])
        self.assertEqual((2300,3,0),(proposals[-1].path[-1],proposals[-1].score,proposals[-1].ticket))

    def test_budget_skipped_prefix_competes_in_same_call(self):
        """Preserved pair work is actually spent on the short qualified route."""
        unit=self.fixture.soldier()
        long=[0]+[-100*i for i in range(1,13)]
        short=[0,-100,-200,-300,-400,-500,-600]
        for candidates,gain,expected,score,ticket in (([short],12,-600,32,1),
                ([],12,-1200,17,0),([short],3,-1200,17,0)):
            remaining,records=[64,128,512],[]
            found,path,value,routine,first=self.choose_route(unit,long,candidates,remaining,records,local_gain=gain)
            self.assertTrue(found)
            self.assertEqual((expected,score,ticket),(path[-1],value,first))
            self.assertEqual((-1,0,"detector_pair_budget"),records[0][1:4])
            if candidates and gain>4:
                self.assertEqual((0,48),records[1][1:3])
                self.assertEqual(16,remaining[0])
            else:
                self.assertEqual(1,len(records))
                self.assertEqual(64,remaining[0])
        # Second blue cannot use the unverified fallback.
        found,_,_,_,ticket=self.choose_route(unit,long,[],[64,128,512],[],second=True)
        self.assertFalse(found)
        self.assertEqual(0,ticket)

    def test_short_alternatives_must_clear_existing_safety_and_score_gates(self):
        """Clear contact alone does not displace a legal prefix."""
        unit=self.fixture.soldier()
        long=[0]+[-100*i for i in range(1,13)]
        short=[0,-100,-200,-300,-400,-500,-600]
        for overrides,expected_score in (
                (dict(local_gain=5,cohesion_gain=8),25), # actual tie
                (dict(stealth_risk=True),17),
                (dict(cover_risk=2),17)):
            with self.subTest(overrides=overrides):
                unit.GetMyTemplate=lambda:NS(bCanTakeCover=True)
                records=[]
                found,path,score,routine,ticket=self.choose_route(
                    unit,long,[short],[64,128,512],records,**overrides)
                self.assertEqual((True,-1200,expected_score,0),(found,path[-1],score,ticket))
                self.assertEqual((0,48),records[1][1:3])
        # A shorter route with positively observed contact cannot displace it.
        unit.GetMyTemplate=lambda:NS(bCanTakeCover=False)
        found,path,score,routine,ticket=self.choose_route(
            unit,long,[[0,1000]],[64,128,512],[])
        self.assertEqual((True,-1200,17,0),(found,path[-1],score,ticket))

    def test_default_budget_tail_can_select_short_route(self):
        """32 detectors and 3 x 10 steps leave 64 pairs for the final alternative."""
        for i in range(9,33):
            self.fixture.detectors[i]=self.fixture.detectors[8]
            self.fixture.refs.append(NS(ObjectID=i))
        remaining,records=[1024,128,512],[]
        for n in range(1,4):
            self.choose_route(self.fixture.soldier(n),[0]+[-100*i for i in range(1,11)],[],remaining,records)
        self.assertEqual(64,remaining[0])
        found,path,score,routine,ticket=self.choose_route(self.fixture.soldier(4),
            [0]+[-100*i for i in range(1,9)],[[0,-100,-200]],remaining,records)
        self.assertEqual((True,-200,32,1),(found,path[-1],score,ticket))
        self.assertEqual(0,remaining[0])
        self.assertEqual([320,320,320,0,64],[r[2] for r in records])

    def test_early_contact_not_certified_by_skipped_preflight(self):
        """An uninspected long route cannot earn a Clear ticket."""
        unit=self.fixture.soldier()
        route=UCArray([0,1000]+[2000+i*100 for i in range(11)])
        legacy=self.assess(unit,route,self.fixture.refs,UCArray(),True,"snapshot",0,64,128,512,"",False)
        self.assertEqual(1,legacy[0])
        records=[]
        found,path,score,routine,ticket=self.choose_route(unit,route,[],[64,128,512],records)
        self.assertEqual((True,route[-1],17,0),(found,path[-1],score,ticket))
        self.assertEqual((-1,0,"detector_pair_budget"),records[0][1:4])

    def test_active_patrol_preserves_original_los_work(self):
        """Execute controller budget routing, real assessor, lanes and variant score."""
        make=function_body(CONTROLLER.read_text(encoding="utf-8-sig"),"MakeDecision")
        start=make.index("if (bPatrolActive)\n                RoutineContactAllowance")
        end=make.index("\n        }\n        if (bCandidateMove",start)
        budget_flow=make[start:end]
        call_start=budget_flow.index("bCandidateMove = ")
        call_end=budget_flow.index(";",call_start)+1
        self.assertIn("RoutineContactAllowance, RemainingContactTiles, RemainingContactLOS",budget_flow[call_start:call_end])
        self.assertIn("bPatrolActive)",budget_flow[call_start:call_end])
        # Out-parameter bridge to the actual route flow, not an independent LOS model.
        budget_flow=budget_flow[:call_start]+(
            "RoutineContactAllowance,RemainingContactTiles,RemainingContactLOS = "
            "Choose(RoutineContactAllowance,RemainingContactTiles,RemainingContactLOS,bPatrolActive);"
        )+budget_flow[call_end:]
        budget_flow+="return (RemainingContactDetectors,RemainingRoutineContactChecks,RemainingContactTiles,RemainingContactLOS);"
        self.fixture.unknown_los=True
        self.fixture.detectors[1].TileLocation=0
        unit=self.fixture.soldier()
        route=UCArray([0]+[100]*12)
        def choose(pairs,tiles,los,preserve):
            """Run actual prefix/local flow on controlled native geometry."""
            remaining=[pairs,tiles,los]
            self.choose_route(unit,route,[],remaining,[],preserve)
            return tuple(remaining)
        budget_run=compile_fragment("Budget","bPatrolActive,RemainingContactDetectors,RemainingRoutineContactChecks,RemainingContactTiles,RemainingContactLOS",budget_flow,dict(Choose=choose))
        active=budget_run(True,64,1024,128,11)
        inactive=budget_run(False,64,1024,128,11)
        self.assertEqual((0,1024,119,3),active)
        self.assertEqual(0,inactive[-1])
        # Variant geometry uses three native LOS samples; adapt vector fields only.
        lanes_body=function_body(PATROL.read_text(encoding="utf-8-sig"),"CountVariantLanes")
        lanes_body=lanes_body.replace("Variant = Target;","Variant = CopyTile(Target);")
        lanes_body=lanes_body.replace("for (Index = 0; Index < 3; ++Index)","for Index in range(3)")
        lanes_body="Lanes = 0; Visibility = MakeVisibility();"+lanes_body
        lanes_body=re.sub(r"return (0|Lanes);",r"return (\1,RemainingLOS);",lanes_body)
        def see(_,__,visibility):
            """All three controlled directional lanes are visible."""
            visibility.DefaultTargetDist=1
            return True
        lanes=compile_fragment("Lanes","Soldier,Position,Target,RemainingLOS",lanes_body,
            dict(XWORLD=NS(IsTileOutOfRange=lambda _:False,CanSeeTileToTile=see),
                 Square=lambda x:x*x,METERSTOUNITS=lambda x:x,MakeVisibility=NS,
                 CopyTile=lambda t:NS(X=t.X,Y=t.Y)))
        shooter=NS(GetVisibilityRadius=lambda:300)
        good=lanes(shooter,NS(X=0,Y=0),NS(X=1,Y=1),active[-1])
        exhausted=lanes(shooter,NS(X=0,Y=0),NS(X=1,Y=1),inactive[-1])
        self.assertEqual((3,0),good)
        self.assertEqual((0,0),exhausted)
        score=load_uc_function(PATROL,"VariantPositionScore")
        self.assertEqual(66,score(4,good[0],True,0,0,-1,8))
        self.assertEqual(-10000,score(4,exhausted[0],True,0,0,-1,8))

    def test_scope_and_shared_budget_are_wired_to_real_controller(self):
        """Keep nonroutine consumers, snapshot caps and LOS/tile limits unchanged."""
        make = function_body(CONTROLLER.read_text(encoding="utf-8-sig"),"MakeDecision")
        self.assertEqual(2,make.count("RemainingRoutineContactChecks = "))
        self.assertIn("RoutineContactAllowance, RemainingContactTiles, RemainingContactLOS",make)
        self.assertIn("RemainingContactDetectors = RoutineContactAllowance",make)
        self.assertIn("RemainingContactDetectors, RemainingContactTiles, RemainingContactLOS",make)
        self.assertEqual(2,self.choose.count("RemainingContactLOS, ContactReason, !bPreservePatrolContactBudget)"))
        self.assertIn("bInspectContact = !bCoverUrgent && !Goal.bImmediateThreats",self.choose)
        self.assertIn("bSecondBlue && ContactStatus != 0",self.choose)
        self.assertIn("if (!bSecondBlue && Path.Length < 2 && RiskyRoute.Length > 1)",self.choose)


if __name__ == "__main__":
    unittest.main()
