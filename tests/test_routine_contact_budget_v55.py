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
                           ("Path", "CandidatePath"), ("Path", "RiskyRoute")):
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
    translated = re.sub(r"\bif __UC_ELIF__\s+and\s+", "elif ", translate_body(body))
    translated = translated.replace("if __UC_ELSE__:", "else:")
    code = "def " + name + "(" + params + "):\n" + translated
    ns = dict(env, UCArray=UCArray)
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

    def run_squad(self, configured, preflight, alternative=True):
        """Use shared budgets and actual prefix/local candidate selection gates.

        Native inputs and competing position gains are fixtures. The existing
        routine branch decides whether to accept, retain caution or fall back.
        """
        remaining = [configured,128,512]
        results = []
        def assess(unit,path,units,interactives,complete,reason,horizon,pairs,tiles,los,detail,require):
            """Model UnrealScript out parameters and capture actual work."""
            before = self.fixture.pair_reads
            result = self.assess(unit,path,units,interactives,complete,reason,horizon,pairs,tiles,los,detail,preflight)
            remaining[:] = result[1:4]
            results.append((unit.ObjectID,result[0],self.fixture.pair_reads-before,result[-1]))
            return result
        env = dict(Contact=NS(AssessRoute=assess,PathStatusPenalty=self.penalty),
                   ApplyConstructiveSoftPenalty=load_uc_function(MISSION,"ApplyConstructiveSoftPenalty"),
                   ScoreOrdinaryRouteCandidate=load_uc_function(MISSION,"ScoreOrdinaryRouteCandidate"),
                   FMin=min,FMax=max,Log=lambda:None,
                   BlueRouteExposureSafe=lambda *_:True,BlueRouteExplosiveSafe=lambda *_:True,
                   Concealment=NS(RouteConcealmentPenalty=lambda *_:0),
                   ConcealmentDefaults=NS(ConcealmentRiskPenalty=18))
        # Prefix inspection and real caution/second-blue/acceptance branch.
        start = self.choose.index("if (bInspectContact)\n                {\n                    ContactStatus")
        end = self.choose.index("// Blue moves preserve",start) if "// Blue moves preserve" in self.choose[start:] else self.choose.index("UnitVisualizer.m_kReachableTilesCache.GetAllPathableTiles",start)
        prefix = self.choose[start:end].rstrip()
        # The enclosing exposure/route blocks were opened before this fragment.
        prefix = prefix[:prefix.rfind("}")].rstrip()
        prefix = prefix[:prefix.rfind("}")].rstrip()
        prefix = prefix[:prefix.rfind("}")].rstrip()
        prefix = prefix.replace("return true;","return (Path,Score,ContactStatus,RiskyRoute,RiskyRouteScore,iFirstBlueClear);")
        prefix = ("RiskyRoute = UCArray(); RiskyRouteScore = 0; ContactReason = \"\";"
                  "bInspectContact = true; bSecondBlue = false; bSingleBlue = true;"
                  "CoverRisk = 0.0; bConcealmentUrgent = true; RouteTempo = none;"
                  "VisibleEnemies = UCArray(); MeleeThreatReaches = UCArray(); ThreatWeights = UCArray();"
                  "CurrentRisk = 0; RemainingTempoCoverChecks = 128; Score = 50; iFirstBlueClear = 0;"
                  + prefix + "return (Path,Score,ContactStatus,RiskyRoute,RiskyRouteScore,iFirstBlueClear);")
        prefix_run = compile_fragment("Prefix",
            "UnitState,Path,ContactUnits,ContactInteractives,bContactSnapshotComplete,ContactSnapshotReason,RemainingContactDetectors,RemainingContactTiles,RemainingContactLOS",
            prefix,env)
        selected = []
        for n,length in ((1,12),(2,8),(3,8),(4,8)):
            path = UCArray([0]+[-100*i for i in range(1,length+1)])
            if n==4:
                path = UCArray([0,100,200,300,1000,2000,2100,2200,2300])
            unit = self.fixture.soldier(n)
            chosen,score,status,risky,risky_score,ticket = prefix_run(unit,path,self.fixture.refs,UCArray(),True,"snapshot",*remaining)
            if chosen.Length < 2:
                # Real local assessment, penalty and retained path assignment.
                # All other native safety checks have passed in this fixture.
                if alternative:
                    start = self.choose.index("if (bSafe)", self.choose.index("++UnsafePathRejected"))
                    end = self.choose.index("\n    }\n    if (!bSecondBlue && Path.Length < 2 && RiskyRoute.Length > 1)",start)
                    local = self.choose[start:end]
                    local = ("bInspectContact = true; bSecondBlue = false; bSingleBlue = true;"
                             "bCoverUrgent = false; bConcealmentUrgent = true; RouteTempo = none;"
                             "VisibleEnemies = UCArray(); MeleeThreatReaches = UCArray(); ThreatWeights = UCArray();"
                             "CurrentRisk = 0; CurrentScore = 0; BestScore = 4; LocalFallbackScore = 4;"
                             "LocalFallbackPath = UCArray(); MemoryFallbackPath = UCArray();"
                             "RemainingTempoCoverChecks = 128; RemainingCoverChecks = 128;"
                             "BestContactStatus = -1; bBestBlueFullyClear = false;"
                             "ContactReason = \"\"; Path = UCArray();"
                             "for CandidatePath in Candidates {"
                             "CandidateScore = 45; CandidateRisk = 0; bSafe = true;"
                             +local+"}\nreturn (Path,BestContactStatus,bBestBlueFullyClear);")
                    local_run = compile_fragment("Local",
                        "UnitState,Candidates,ContactUnits,ContactInteractives,bContactSnapshotComplete,ContactSnapshotReason,RemainingContactDetectors,RemainingContactTiles,RemainingContactLOS",local,env)
                    candidate = UCArray([0,-100,-200,-300,-400,-500,-600])
                    chosen,status,first_clear = local_run(unit,[candidate],self.fixture.refs,UCArray(),True,"snapshot",*remaining)
                    # Execute the existing final first-blue ticket assignment.
                    ticket_source = self.choose[self.choose.index("iAcceptedRoutine = (bInspectContact && !bUsedLocalFallback)"):].replace("return true;","return iFirstBlueClear;")
                    ticket = compile_fragment("Ticket","bInspectContact,bUsedLocalFallback,bSingleBlue,bBestBlueFullyClear",ticket_source,env)(True,False,True,first_clear)
                start = self.choose.index("if (!bSecondBlue && Path.Length < 2 && RiskyRoute.Length > 1)")
                end = self.choose.index("if (!bSecondBlue && Path.Length < 2 && LocalFallbackPath.Length > 1)",start)
                fallback = self.choose[start:end].replace("return true;","return (Path,RiskyContactStatus);")
                fallback += "\nreturn (Path,ContactStatus);"
                chosen,status = compile_fragment("Fallback",
                    "UnitState,bSecondBlue,Path,RiskyRoute,RiskyRouteScore,RiskyRouteCoverRisk,bInspectContact,RiskyContactStatus,RiskyContactReason,ContactStatus",
                    fallback,env)(unit,False,chosen,risky,risky_score,0,True,1,"fixture",status)
            selected.append((n,chosen[-1],status,ticket))
        return results,selected,remaining

    def test_four_soldiers_old_and_new_budget(self):
        """Compare actual started/completed inspections and useful safe alternative."""
        old,old_selected,left = self.run_squad(64,False)
        self.assertEqual((4,1,0), (len(old),sum(x[2]>0 for x in old),sum(x[1]>=0 for x in old)))
        self.assertEqual(0,left[0])
        self.assertEqual(2300,old_selected[-1][1])
        self.assertEqual(-1,old_selected[-1][2])
        self.fixture.pair_reads = self.fixture.los_reads = 0
        new,selected,left = self.run_squad(self.budget(1024),True)
        self.assertEqual((5,5,5),(len(new),sum(x[2]>0 for x in new),sum(x[1]>=0 for x in new)))
        self.assertEqual([0,0,0,1,0],[x[1] for x in new])
        self.assertEqual((4,-600,0,1),selected[-1])
        self.assertEqual(297,self.fixture.pair_reads)
        self.assertEqual(1024-297,left[0])
        self.assertGreaterEqual(left[1],0)
        self.assertGreaterEqual(left[2],0)

    def test_only_legal_caution_prefix_remains_usable(self):
        """No qualified alternative does not force the squad to idle."""
        results,selected,_ = self.run_squad(self.budget(1024),True,False)
        self.assertEqual(1,results[-1][1])
        self.assertEqual((4,2300,1,0),selected[-1])

    def test_scope_and_shared_budget_are_wired_to_real_controller(self):
        """Keep nonroutine consumers, snapshot caps and LOS/tile limits unchanged."""
        make = function_body(CONTROLLER.read_text(encoding="utf-8-sig"),"MakeDecision")
        self.assertEqual(1,make.count("RemainingRoutineContactChecks = "))
        self.assertIn("RemainingRoutineContactChecks, RemainingContactTiles, RemainingContactLOS",make)
        self.assertIn("RemainingContactDetectors, RemainingContactTiles, RemainingContactLOS",make)
        self.assertEqual(2,self.choose.count("RemainingContactLOS, ContactReason, true)"))
        self.assertIn("bInspectContact = !bCoverUrgent && !Goal.bImmediateThreats",self.choose)
        self.assertIn("bSecondBlue && ContactStatus != 0",self.choose)
        self.assertIn("if (!bSecondBlue && Path.Length < 2 && RiskyRoute.Length > 1)",self.choose)


if __name__ == "__main__":
    unittest.main()
