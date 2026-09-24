import asyncio

def clip(text: str, limit: int = 3000) -> str:
    """Keep the tail of long output, where errors usually are."""
    return text if len(text) <= limit else "...(truncated)\n" + text[-limit:]


async def run_process(args: list[str], stdin: str | None = None, timeout: int = 60) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL if stdin is None else asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as e:
        return f"Could not start the command: {e}"

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(None if stdin is None else stdin.encode()),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"Command timed out after {timeout} seconds."

    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()

    parts = [f"Exit code: {proc.returncode}"]
    if out:
        parts.append(f"stdout:\n{clip(out)}")
    if err:
        parts.append(f"stderr:\n{clip(err)}")
    if not out and not err:
        parts.append("(no output)")
    return "\n".join(parts)