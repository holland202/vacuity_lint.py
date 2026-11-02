Independent synthetic cases reproduce three preservation defects in `suite_mutation_probe.py`: preexisting `_smp_cov` files are overwritten, an existing `<source>.mutbak` is overwritten and deleted, and CRLF source bytes are normalized during restoration, triggering a fatal hash mismatch.

The preregistration commit precedes execution. Honest and theatre controls reproduce their expected scores and preserve their trees. An isolated cleanup mutant is caught by an independent before/after oracle. The attack runner exits 1 for the three preservation failures; exact commands, raw streams, file hashes and changed bytes are included under `review/smp_chatgpt_20261102/`.

Frozen target: `c1ca2d4ee489b5d64285fa6600f46d5f948296a3`. This is a bounded review; the earlier attack brief was not recovered and full coverage of that brief is not claimed. No production code was changed; fixes are separate. No merge is authorized.

ChatGPT (OpenAI) designed and ran this review → human validation: not performed → human responsibility: Chad Holland.
