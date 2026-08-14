# Rollback Procedure for Gemini Scoring Engine

## Reverting the Active Provider
Rollback is a purely configurational operation since the original legacy deterministic heuristic scoring path was safely preserved.

To rollback:
1. Change the AI Provider flag:
   ```env
   AI_PROVIDER=openai
   ```
2. This will re-enable the original deterministic Python heuristic scoring implementation (`calculate_skills_matching`, etc). **This is NOT an OpenAI API fallback**, it is the deterministic heuristic implementation.
3. Restart the application or trigger a Vercel redeployment to reload `get_settings()`.

## Code Rollback (Hard Revert)
If a structural revert of this specific phase is necessary:
1. Revert `apps/api/hiron/scores/engine.py` to `HEAD^` to strip the `httpx` HTTP calls.
2. Remove `AIGeneratedScore` from `apps/api/hiron/scores/schemas.py`.
3. Delete `apps/api/tests/test_scores_engine_gemini.py`.
4. Delete `docs/phase_21_4_gemini_scoring_poc/`.
